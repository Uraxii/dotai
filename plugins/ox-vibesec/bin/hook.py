import json
import os
import re
import subprocess
import sys
from pathlib import Path
from time import monotonic

import vibesec
from patch_replay import patch_writes


PATCH_CHECK_BUDGET = 23


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
        tool = data.get("tool_name")
        if not isinstance(args, dict):
            return None
        if tool == "exec" and isinstance(args.get("command"), str):
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


def ox_payloads(event, data, cwd):
    if event not in ("PreToolUse", "PostToolUse") or data.get("tool_name") != "apply_patch":
        payload = ox_payload(event, data, cwd)
        return [payload] if payload else []
    args = data.get("tool_input")
    text = args.get("input") if isinstance(args, dict) else None
    if not isinstance(text, str) or not text.strip():
        return []
    post = event == "PostToolUse"
    if post:
        response = data.get("tool_response")
        if not isinstance(response, dict) or response.get("success") is not True:
            return []
    try:
        writes = patch_writes(text, cwd, post=post)
    except (OSError, ValueError):
        writes = []
    if not writes:
        print("OX VibeSec could not parse patch; check skipped.", file=sys.stderr)
    payloads = []
    for index, write in enumerate(writes, 1):
        payload = ox_payload(event, {**data, "tool_name": "write", "tool_input": write}, cwd)
        if not payload:
            return []
        if len(writes) > 1 and "tool_use_id" in payload:
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
