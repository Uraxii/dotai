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
        elif data.get("tool_name") == "edit":
            path = args.get("file_path") or args.get("path")
            if not isinstance(path, str):
                return None
            if isinstance(args.get("content"), str):
                payload.update(tool_name="Write", tool_input={"file_path": path, "content": args["content"]})
            elif isinstance(args.get("new_string"), str):
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


def run():
    event = sys.argv[1]
    key = os.environ.get("OX_VIBESEC_API_KEY", "").strip()
    if not key:
        return 0
    data = json.load(sys.stdin)
    if not isinstance(data, dict):
        return 0
    cwd = Path(os.environ.get("DEVIN_PROJECT_DIR") or os.getcwd())
    payload = ox_payload(event, data, cwd)
    if not payload:
        return 0
    home = Path.home()
    runtime = vibesec.Runtime(
        home / ".local/state/ox-vibesec-devin/home",
        home / ".local/lib/ox-vibesec-devin/install.sh",
    )
    result = runtime.run(payload, cwd, key, initialize=event == "SessionStart")
    if result is None:
        if event != "SessionStart":
            print("OX VibeSec runtime is not initialized; check skipped.", file=sys.stderr)
        return 0
    if result.returncode == 2:
        print("OX VibeSec blocked this action.", file=sys.stderr)
        return 2
    if result.returncode:
        raise RuntimeError("hook")
    if result.stdout.strip():
        reply = json.loads(result.stdout)
        output = reply.get("hookSpecificOutput") if isinstance(reply, dict) else None
        if not isinstance(output, dict):
            return 0
        reason = output.get("permissionDecisionReason", "")
        if event == "PreToolUse" and output.get("permissionDecision") == "deny":
            print(json.dumps({"decision": "block", "reason": str(reason).replace(key, "[redacted]") or "OX VibeSec blocked this action."}))
        elif output.get("hookEventName") == event and isinstance(output.get("additionalContext"), str):
            context = output["additionalContext"].replace(key, "[redacted]")
            print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):
        print("OX VibeSec hook unavailable.", file=sys.stderr)
        raise SystemExit(1)
