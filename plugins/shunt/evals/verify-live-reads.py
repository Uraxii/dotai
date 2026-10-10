#!/usr/bin/env python3
"""Check the retained live tool traces, denial continuation, and answers."""

import json
from pathlib import Path

TRANSCRIPTS = Path(__file__).parent / "transcripts"
ROUTES = "routes.txt"
EXPECTED_ANSWER = ("billing", "search", "checkout", "23", "239", "467", "21")


def read_events(name: str) -> list[dict]:
    return [json.loads(line) for line in (TRANSCRIPTS / name).read_text().splitlines()]


def check_answer(text: str) -> None:
    assert all(value in text for value in EXPECTED_ANSWER), text
    assert "route-001:" not in text, "Full file entered the parent's answer"


def check_claude() -> None:
    events = read_events("claude-reader.jsonl")
    calls = []
    for event in events:
        if event["type"] == "assistant":
            for block in event["message"]["content"]:
                if block["type"] == "tool_use":
                    calls.append((event.get("parent_tool_use_id"), block))
    agents = [call for parent, call in calls if not parent and call["name"] == "Agent"]
    assert len(agents) == 1
    assert all(not parent for parent, call in calls if call["name"] == "Agent")
    assert all("portal-cli" not in str(call["input"]) for _, call in calls)
    assert agents[0]["input"]["subagent_type"] == "Explore"
    assert agents[0]["input"]["model"] == "haiku"
    for parent, call in calls:
        if not parent and call["name"] == "Read":
            assert ROUTES not in call["input"].get("file_path", "")
        if not parent and call["name"] == "Bash":
            assert call["input"]["command"].startswith("grep ")
    chunks = [call["input"].get("command", "") for parent, call in calls if parent]
    assert any("1,350p" in command for command in chunks)
    assert any("351,480p" in command for command in chunks)
    denied = [block for event in events if event["type"] == "user"
              for block in event["message"]["content"] if block.get("is_error")]
    assert any("reader subagent; do not delegate again" in str(b) for b in denied)
    result = next(event for event in events if event["type"] == "result")
    assert not result["is_error"]
    check_answer(result["result"])
    for event in events:
        if event["type"] == "user" and not event.get("parent_tool_use_id"):
            assert "route-001:" not in json.dumps(event["message"]["content"])
    print("PASS Claude: Explore/haiku, subagent denial then chunks, correct answer")


def check_copilot(name: str, model: str, subagent_denial: bool) -> None:
    events = read_events(name)
    calls = [e for e in events if e["type"] == "tool.execution_start"]
    tasks = [e for e in calls if not e.get("agentId") and e["data"]["toolName"] == "task"]
    assert len(tasks) == 1
    assert all(not e.get("agentId") for e in calls if e["data"]["toolName"] == "task")
    assert all("portal-cli" not in str(e["data"]["arguments"]) for e in calls)
    assert all(e["data"]["toolName"] in {"skill", "task", "view"}
               for e in calls if not e.get("agentId"))
    args = tasks[0]["data"]["arguments"]
    assert args["agent_type"] == "explore" and args["mode"] == "sync"
    started = next(e for e in events if e["type"] == "subagent.started")
    assert started["data"]["model"] == model
    if model == "gpt-5.4-mini":
        assert args["model"] == model
    completions = {e["data"]["toolCallId"]: e["data"] for e in events
                   if e["type"] == "tool.execution_complete"}
    views = [e for e in calls if e["data"]["toolName"] == "view"]
    for event in views:
        if not event.get("agentId"):
            result = completions[event["data"]["toolCallId"]]
            assert not result["success"] and result["error"]["code"] == "denied"
    ranges = [e["data"]["arguments"].get("view_range") for e in views if e.get("agentId")]
    assert [1, 350] in ranges and [351, 480] in ranges
    if subagent_denial:
        assert any(e.get("agentId") and not e["data"]["success"]
                   and "do not delegate again" in str(e["data"])
                   for e in events if e["type"] == "tool.execution_complete")
    text = "\n".join(e["data"].get("content", "") for e in events
                     if e["type"] == "assistant.message" and not e.get("agentId"))
    check_answer(text)
    check_answer(completions[tasks[0]["data"]["toolCallId"]]["result"]["content"])
    print(f"PASS Copilot: explore/{model}, chunks, correct concise parent answer")


def check_hook_identity() -> None:
    claude = read_events("claude-hook-inputs.jsonl")
    copilot = read_events("copilot-hook-inputs.jsonl")
    assert any(event.get("agent_id") and event.get("tool_name") == "Read"
               for event in claude)
    assert all(set(event) == {"cwd", "sessionId", "timestamp", "toolArgs", "toolName"}
               for event in copilot)
    print("PASS hook inputs: Claude agent_id; Copilot has no subagent role field")


if __name__ == "__main__":
    check_claude()
    check_copilot("copilot-reader.jsonl", "gpt-5.4-mini", False)
    check_copilot("copilot-subagent-denial.jsonl", "gpt-5.6-luna", True)
    check_hook_identity()
