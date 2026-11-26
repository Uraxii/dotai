import json
import os
import re
import subprocess
import sys
from pathlib import Path
from time import monotonic

import vibesec


PATCH_CHECK_BUDGET = 23


def ox_payload(event, data, cwd, *, patch_edit=None):
    session_id = data.get("session_id", "")
    if not isinstance(session_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", session_id):
        return None
    payload = {"hook_event_name": event, "session_id": session_id, "cwd": str(cwd)}
    if event == "SessionStart":
        payload["source"] = "resume" if data.get("source") == "resume" else "startup"
    elif event == "UserPromptSubmit":
        if not isinstance(data.get("prompt"), str):
            return None
        payload["prompt"] = data["prompt"]
    else:
        args = patch_edit if patch_edit is not None else data.get("tool_input")
        tool = "edit" if patch_edit is not None else data.get("tool_name")
        if not isinstance(args, dict):
            return None
        if patch_edit is not None and "edits" in patch_edit:
            payload.update(tool_name="MultiEdit", tool_input=patch_edit)
        elif tool == "exec" and isinstance(args.get("command"), str):
            payload.update(tool_name="Bash", tool_input={"command": args["command"]})
        elif tool in ("edit", "write"):
            path = args.get("file_path") or args.get("path")
            if not isinstance(path, str):
                return None
            if isinstance(args.get("content"), str):
                payload.update(tool_name="Write", tool_input={"file_path": path, "content": args["content"]})
            elif tool == "edit" and isinstance(args.get("new_string"), str):
                payload.update(tool_name="Edit", tool_input={"file_path": path, "new_string": args["new_string"]})
                if isinstance(args.get("old_string"), str):
                    payload["tool_input"]["old_string"] = args["old_string"]
            else:
                return None
        else:
            return None
        if isinstance(data.get("tool_use_id"), str):
            payload["tool_use_id"] = data["tool_use_id"]
        if event == "PostToolUse":
            response = data.get("tool_response")
            if not isinstance(response, dict):
                return None
            output = response.get("output")
            error = response.get("error")
            payload["tool_response"] = {
                "success": response.get("success") is True,
                "stdout": output if isinstance(output, str) else "",
                "stderr": error if isinstance(error, str) else "",
            }
    return payload


def patch_edits(text, event):
    if not isinstance(text, str):
        return []
    lines = text.replace("\r\n", "\n").strip().split("\n")
    wrapper = re.fullmatch(r"""(?:apply_patch[ \t]+)?<<[ \t]*(['"]?)([A-Za-z_]\w*)\1""", lines[0])
    if wrapper and lines[-1] == wrapper[2]:
        lines = lines[1:-1]
    if len(lines) < 2:
        return []
    if lines[0].strip() != "*** Begin Patch" or lines[-1].strip() != "*** End Patch":
        return []
    body = "\n".join([*lines[1:-1], ""]).lstrip("\n \t")
    if body.startswith("*** Environment ID: "):
        body = body.partition("\n")[2].lstrip("\n \t")
    prefix, *sections = re.split(
        r"^\*\*\* (Add|Update|Delete) File: (.+)\n", body, flags=re.MULTILINE,
    )
    if prefix:
        return []
    edits = []
    for operation, path, section in zip(sections[::3], sections[1::3], sections[2::3]):
        path = path.strip()
        if not path:
            return []
        lines = section.removesuffix("\n").split("\n") if section else []
        lines = [line for line in lines if line != r"\ No newline at end of file"]
        if operation == "Delete":
            if lines:
                return []
            continue
        if operation == "Add":
            if any(not line.startswith("+") for line in lines):
                return []
            edits.append({"file_path": path, "content": "".join(line[1:] + "\n" for line in lines)})
            continue
        if lines and lines[0].startswith("*** Move to: "):
            destination = lines.pop(0).removeprefix("*** Move to: ").strip()
            if not destination:
                return []
            if event == "PostToolUse":
                path = destination
        hunks = []
        changes = []
        for line in [*lines, "@@"]:
            if line.rstrip() in ("@@", "*** End of File") or line.startswith("@@ "):
                if any(entry[0] in "+-" for entry in changes):
                    hunks.append({
                        "old_string": "\n".join(entry[1:] for entry in changes if entry[0] != "+"),
                        "new_string": "\n".join(entry[1:] for entry in changes if entry[0] != "-"),
                    })
                changes = []
            elif not line or line[0] in " +-":
                changes.append(line or " ")
            else:
                return []
        if hunks:
            edits.append({"file_path": path, "edits": hunks})
    return edits


def ox_payloads(event, data, cwd):
    if event not in ("PreToolUse", "PostToolUse") or data.get("tool_name") != "apply_patch":
        payload = ox_payload(event, data, cwd)
        return [payload] if payload else []
    args = data.get("tool_input")
    text = args.get("input") if isinstance(args, dict) else None
    edits = patch_edits(text, event)
    if not edits and isinstance(text, str) and text.strip():
        print("OX VibeSec could not parse patch; check skipped.", file=sys.stderr)
    payloads = []
    for index, edit in enumerate(edits, 1):
        parts = [edit]
        if event == "PostToolUse" and "edits" in edit:
            parts = [{"file_path": edit["file_path"], **hunk} for hunk in edit["edits"]]
        for part_index, part in enumerate(parts):
            payload = ox_payload(event, data, cwd, patch_edit=part)
            if not payload:
                return []
            if "tool_use_id" in payload:
                if len(edits) > 1:
                    payload["tool_use_id"] += f":{index}"
                if part_index:
                    payload["tool_use_id"] += f":{part_index}"
            payloads.append(payload)
    return payloads


def run():
    event = sys.argv[1]
    key = os.environ.get("OX_VIBESEC_API_KEY", "").strip()
    if not key:
        return 0
    data = json.load(sys.stdin)
    if not isinstance(data, dict):
        return 0
    cwd = Path(os.environ.get("DEVIN_PROJECT_DIR") or os.getcwd())
    deadline = monotonic() + PATCH_CHECK_BUDGET if data.get("tool_name") == "apply_patch" else None
    payloads = ox_payloads(event, data, cwd)
    if not payloads:
        return 0
    installer = os.environ.get("OX_VIBESEC_INSTALLER")
    runtime = vibesec.Runtime(
        Path.home() / ".local/state/ox-vibesec-devin/home",
        Path(installer) if installer else None,
    )
    failed = False
    budget_exhausted = False
    contexts = []
    options = {"deadline": deadline} if deadline is not None else {}
    for payload in payloads:
        if deadline is not None and monotonic() >= deadline:
            budget_exhausted = True
            break
        try:
            result = runtime.run(payload, cwd, key, initialize=event == "SessionStart", **options)
            if result is None:
                if event != "SessionStart":
                    print("OX VibeSec runtime is not initialized; check skipped.", file=sys.stderr)
                break
            if result.returncode == 2:
                reason = result.stderr.strip().replace(key, "[redacted]")
                print(reason or "OX VibeSec blocked this action.", file=sys.stderr)
                return 2
            if result.returncode:
                failed = True
                continue
            reply = json.loads(result.stdout) if result.stdout.strip() else None
        except subprocess.TimeoutExpired:
            if deadline is not None and monotonic() >= deadline:
                budget_exhausted = True
                break
            failed = True
            continue
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):
            failed = True
            continue
        output = reply.get("hookSpecificOutput") if isinstance(reply, dict) else None
        if not isinstance(output, dict):
            continue
        reason = output.get("permissionDecisionReason", "")
        if event == "PreToolUse" and output.get("permissionDecision") == "deny":
            print(json.dumps({"decision": "block", "reason": str(reason).replace(key, "[redacted]") or "OX VibeSec blocked this action."}))
            return 0
        if output.get("hookEventName") == event and isinstance(output.get("additionalContext"), str):
            contexts.append(output["additionalContext"].replace(key, "[redacted]"))
    if budget_exhausted:
        print("OX VibeSec: check skipped (time budget)", file=sys.stderr)
    if contexts:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": "\n\n".join(contexts)}}))
    if failed:
        if not contexts and not budget_exhausted:
            raise RuntimeError("hook")
        print("OX VibeSec hook unavailable.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):
        print("OX VibeSec hook unavailable.", file=sys.stderr)
        raise SystemExit(1)
