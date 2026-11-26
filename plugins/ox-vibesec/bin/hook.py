import json
import os
import re
import subprocess
import sys
from pathlib import Path

import vibesec


def ox_payload(event, data, cwd):
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
        args = data.get("tool_input")
        if not isinstance(args, dict):
            return None
        if data.get("tool_name") == "exec" and isinstance(args.get("command"), str):
            payload.update(tool_name="Bash", tool_input={"command": args["command"]})
        elif data.get("tool_name") in ("edit", "write"):
            path = args.get("file_path") or args.get("path")
            if not isinstance(path, str):
                return None
            if isinstance(args.get("content"), str):
                payload.update(tool_name="Write", tool_input={"file_path": path, "content": args["content"]})
            elif data.get("tool_name") == "edit" and isinstance(args.get("new_string"), str):
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
    if lines[0].strip() != "*** Begin Patch" or lines[-1].strip() != "*** End Patch":
        return []
    body = lines[1:-1]
    if body and body[0].startswith("*** Environment ID: "):
        body = body[1:]
    prefix, *sections = re.split(
        r"^\*\*\* (Add|Update|Delete) File: (.+)\n", "\n".join([*body, ""]), flags=re.MULTILINE,
    )
    if prefix:
        return []
    edits = []
    for operation, path, section in zip(sections[::3], sections[1::3], sections[2::3]):
        lines = section.removesuffix("\n").split("\n") if section else []
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
            destination = lines.pop(0).removeprefix("*** Move to: ")
            if not destination:
                return []
            if event == "PostToolUse":
                path = destination
        hunk = []
        for line in [*lines, "@@"]:
            if line.rstrip() in ("@@", "*** End of File") or line.startswith("@@ "):
                if any(entry.startswith(("-", "+")) for entry in hunk):
                    edits.append({
                        "file_path": path,
                        "old_string": "\n".join(entry[1:] for entry in hunk if entry[0] != "+"),
                        "new_string": "\n".join(entry[1:] for entry in hunk if entry[0] != "-"),
                    })
                hunk = []
            elif not line or line[0] in " +-":
                hunk.append(line or " ")
            else:
                return []
    return edits


def ox_payloads(event, data, cwd):
    if event not in ("PreToolUse", "PostToolUse") or data.get("tool_name") != "apply_patch":
        payload = ox_payload(event, data, cwd)
        return [payload] if payload else []
    args = data.get("tool_input")
    edits = patch_edits(args.get("input"), event) if isinstance(args, dict) else []
    payloads = []
    for index, edit in enumerate(edits, 1):
        payload = ox_payload(event, {**data, "tool_name": "edit", "tool_input": edit}, cwd)
        if not payload:
            return []
        if len(edits) > 1 and "tool_use_id" in payload:
            payload["tool_use_id"] += f":{index}"
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
    payloads = ox_payloads(event, data, cwd)
    if not payloads:
        return 0
    installer = os.environ.get("OX_VIBESEC_INSTALLER")
    runtime = vibesec.Runtime(
        Path.home() / ".local/state/ox-vibesec-devin/home",
        Path(installer) if installer else None,
    )
    failed = False
    contexts = []
    for payload in payloads:
        try:
            result = runtime.run(payload, cwd, key, initialize=event == "SessionStart")
            if result is None:
                if event != "SessionStart":
                    print("OX VibeSec runtime is not initialized; check skipped.", file=sys.stderr)
                return 0
            if result.returncode == 2:
                reason = result.stderr.strip().replace(key, "[redacted]")
                print(reason or "OX VibeSec blocked this action.", file=sys.stderr)
                return 2
            if result.returncode:
                failed = True
                continue
            reply = json.loads(result.stdout) if result.stdout.strip() else None
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
    if failed:
        raise RuntimeError("hook")
    if contexts:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": "\n\n".join(contexts)}}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):
        print("OX VibeSec hook unavailable.", file=sys.stderr)
        raise SystemExit(1)
