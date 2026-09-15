#!/usr/bin/env python3
"""Render Claude and Codex remaining-usage status lines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import getpass
import json
import math
import os
from pathlib import Path
import re
import socket
import sys
import time
from collections.abc import Iterable, Mapping

__all__ = ["main"]

BAR_WIDTH = 10
LINE_LABEL_WIDTH = len("claude")
CODEX_TAIL_BYTES = 256 * 1024
MAX_ROLLOUT_FILES = 3
FIVE_HOUR_MINUTES = 300
WEEKLY_MINUTES = 10_080
WARN = "\033[33m"
DIM = "\033[2;36m"
RESET = "\033[0m"
BATTERY_PATH = Path("/sys/class/power_supply/BAT0")
BATTERY_ICONS = ("󰁺", "󰁻", "󰁼", "󰁽", "󰁾", "󰁿", "󰂀", "󰂁", "󰂂", "󰁹")


@dataclass(frozen=True)
class UsageWindow:
    remaining_percent: float | None


@dataclass(frozen=True)
class UsageSnapshot:
    context: UsageWindow
    five_hour: UsageWindow
    weekly: UsageWindow
    observed_at: datetime | None = None


UNKNOWN_WINDOW = UsageWindow(None)
UNKNOWN_SNAPSHOT = UsageSnapshot(UNKNOWN_WINDOW, UNKNOWN_WINDOW, UNKNOWN_WINDOW)


def as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, dict) else {}


def as_number(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return float(value)
    return None


def bounded_percent(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(100.0, value))


def remaining_from_used(used_percent: object) -> UsageWindow:
    used_number = as_number(used_percent)
    return UsageWindow(bounded_percent(None if used_number is None else 100 - used_number))


def parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def remaining_from_limit(limit: object, now_epoch: float) -> UsageWindow:
    limit_data = as_mapping(limit)
    reset_at = as_number(limit_data.get("resets_at"))
    if reset_at is not None and reset_at <= now_epoch:
        return UsageWindow(100.0)
    return remaining_from_used(limit_data.get("used_percent"))


def claude_snapshot(input_data: Mapping[str, object]) -> UsageSnapshot:
    context_data = as_mapping(input_data.get("context_window"))
    rate_limits = as_mapping(input_data.get("rate_limits"))
    remaining = as_number(context_data.get("remaining_percentage"))
    context = UsageWindow(bounded_percent(remaining))
    if context.remaining_percent is None:
        context = remaining_from_used(context_data.get("used_percentage"))
    return UsageSnapshot(
        context=context,
        five_hour=remaining_from_used(
            as_mapping(rate_limits.get("five_hour")).get("used_percentage")
        ),
        weekly=remaining_from_used(as_mapping(rate_limits.get("seven_day")).get("used_percentage")),
    )


def windows_from_rate_limits(rate_limits: object, now_epoch: float) -> dict[int, UsageWindow]:
    windows: dict[int, UsageWindow] = {}
    for slot in ("primary", "secondary"):
        limit_data = as_mapping(as_mapping(rate_limits).get(slot))
        minutes = as_number(limit_data.get("window_minutes"))
        if minutes is not None:
            windows[int(minutes)] = remaining_from_limit(limit_data, now_epoch)
    return windows


def codex_snapshot(event: Mapping[str, object], now_epoch: float) -> UsageSnapshot:
    payload = as_mapping(event.get("payload"))
    windows = windows_from_rate_limits(payload.get("rate_limits"), now_epoch)
    return UsageSnapshot(
        context=UNKNOWN_WINDOW,
        five_hour=windows.get(FIVE_HOUR_MINUTES, UNKNOWN_WINDOW),
        weekly=windows.get(WEEKLY_MINUTES, UNKNOWN_WINDOW),
        observed_at=parse_timestamp(event.get("timestamp")),
    )


def tail_lines(path: Path) -> list[bytes]:
    try:
        with path.open("rb") as rollout_file:
            rollout_file.seek(0, 2)
            size = rollout_file.tell()
            rollout_file.seek(max(0, size - CODEX_TAIL_BYTES))
            if size > CODEX_TAIL_BYTES:
                rollout_file.readline()
            return rollout_file.read().splitlines()
    except OSError:
        return []


def token_events(paths: Iterable[Path]) -> Iterable[Mapping[str, object]]:
    for path in paths:
        for line in reversed(tail_lines(path)):
            try:
                event = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            payload = as_mapping(as_mapping(event).get("payload"))
            if payload.get("type") == "token_count":
                yield as_mapping(event)


def newest_rollouts(sessions_path: Path) -> list[Path]:
    try:
        files = sessions_path.glob("**/rollout-*.jsonl")
        rollouts = sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)
        return rollouts[:MAX_ROLLOUT_FILES]
    except OSError:
        return []


def codex_usage_snapshot(codex_home: Path, now_epoch: float) -> UsageSnapshot:
    for event in token_events(newest_rollouts(codex_home / "sessions")):
        return codex_snapshot(event, now_epoch)
    return UNKNOWN_SNAPSHOT


def rounded_percent(value: float) -> int:
    return int(value + 0.5)


def make_bar(label: str, window: UsageWindow, warn_at: float | None = None) -> str:
    if window.remaining_percent is None:
        return f"{label} [{'?' * BAR_WIDTH}] {'?':>4}"
    percent = rounded_percent(window.remaining_percent)
    filled = min(BAR_WIDTH, max(0, rounded_percent(percent / BAR_WIDTH)))
    bar = "█" * filled + "░" * (BAR_WIDTH - filled)
    rendered = f"{label} [{bar}] {percent:>3}%"
    if warn_at is not None and window.remaining_percent <= warn_at:
        return f"{WARN}{rendered}{RESET}"
    return rendered


def tokens_per_minute(input_data: Mapping[str, object]) -> str:
    context = as_mapping(input_data.get("context_window"))
    cost = as_mapping(input_data.get("cost"))
    input_tokens = as_number(context.get("total_input_tokens"))
    output_tokens = as_number(context.get("total_output_tokens"))
    duration_ms = as_number(cost.get("total_duration_ms"))
    if input_tokens is None or output_tokens is None or not duration_ms:
        return ""
    tokens_per_min = int((input_tokens + output_tokens) * 60_000 / duration_ms)
    if tokens_per_min <= 0:
        return ""
    context_size = as_number(context.get("context_window_size"))
    if context_size is not None:
        minutes_left = (context_size - input_tokens - output_tokens) / tokens_per_min
        if minutes_left < 60:
            return f"{WARN}⚡{tokens_per_min} (⛃/min){RESET}"
    return f"{tokens_per_min} (⛃/min)"


def battery_status() -> str:
    try:
        capacity = int((BATTERY_PATH / "capacity").read_text().strip())
        status = (BATTERY_PATH / "status").read_text().strip()
    except (OSError, ValueError):
        return ""
    if status == "Charging":
        icon = "󰂄"
    elif status == "Full":
        icon = "󰁹"
    else:
        icon = BATTERY_ICONS[min(9, max(0, capacity // 10))]
    rendered = f"{icon} {capacity}%"
    if capacity <= 20 and status not in {"Charging", "Full"}:
        return f"{WARN}{rendered}{RESET}"
    return rendered


def snapshot_line(
    label: str,
    snapshot: UsageSnapshot,
    age: str = "",
    include_context: bool = True,
) -> str:
    bars = (
        make_bar("5h", snapshot.five_hour, 20),
        make_bar("wk", snapshot.weekly, 50),
    )
    if include_context:
        bars += (make_bar("ctx", snapshot.context),)
    return f"{label:<{LINE_LABEL_WIDTH}} " + "  ".join(bars) + age


def age_suffix(observed_at: datetime | None, now: datetime) -> str:
    if observed_at is None:
        return ""
    seconds = max(0, int((now - observed_at).total_seconds()))
    if seconds < 60:
        age = "<1m"
    elif seconds < 3600:
        age = f"{seconds // 60}m"
    elif seconds < 86_400:
        age = f"{seconds // 3600}h"
    else:
        age = f"{seconds // 86_400}d"
    return f"  {DIM}· {age} ago{RESET}"


def render_status(input_data: Mapping[str, object], codex_home: Path, now_epoch: float) -> str:
    now = datetime.fromtimestamp(now_epoch, UTC)
    user_host = f"{DIM}{getpass.getuser()}@{socket.gethostname().split('.')[0]}{RESET}"
    first_parts = [user_host, battery_status(), tokens_per_minute(input_data)]
    line_one = "  ".join(part for part in first_parts if part)
    codex = codex_usage_snapshot(codex_home, now_epoch)
    claude_line = snapshot_line("claude", claude_snapshot(input_data))
    codex_line = snapshot_line(
        "codex", codex, age_suffix(codex.observed_at, now), include_context=False
    )
    return "\n".join((line_one, claude_line, codex_line))


def parse_stdin() -> Mapping[str, object]:
    try:
        return as_mapping(json.load(sys.stdin))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}


def self_check() -> None:
    now = 1_000.0
    rate_limits = {
        "primary": {
            "used_percent": 25,
            "window_minutes": WEEKLY_MINUTES,
            "resets_at": now + 1,
        }
    }
    windows = windows_from_rate_limits(rate_limits, now)
    assert windows[WEEKLY_MINUTES].remaining_percent == 75
    assert FIVE_HOUR_MINUTES not in windows
    event = {"payload": {"type": "token_count", "rate_limits": rate_limits}}
    assert codex_snapshot(event, now).five_hour.remaining_percent is None
    assert parse_timestamp("2026-09-15T01:00:00") is None
    expired = {"used_percent": 90, "window_minutes": FIVE_HOUR_MINUTES, "resets_at": now}
    assert remaining_from_limit(expired, now).remaining_percent == 100
    nan_rate_limits = {"primary": {"window_minutes": float("nan")}}
    assert windows_from_rate_limits(nan_rate_limits, now) == {}
    cases = (
        (UsageSnapshot(UsageWindow(25), UsageWindow(75), UsageWindow(51)), False),
        (UNKNOWN_SNAPSHOT, False),
        (UsageSnapshot(UsageWindow(100), UsageWindow(100), UsageWindow(100)), False),
        (UsageSnapshot(UsageWindow(5), UsageWindow(5), UsageWindow(5)), True),
    )
    for snapshot, expect_warning in cases:
        claude_line = snapshot_line("claude", snapshot)
        codex_line = snapshot_line("codex", snapshot, include_context=False)
        if expect_warning:
            assert WARN in claude_line
            assert WARN in codex_line
        plain_claude = re.sub(r"\x1b\[[0-9;]*m", "", claude_line)
        plain_codex = re.sub(r"\x1b\[[0-9;]*m", "", codex_line)
        assert "ctx" not in plain_codex
        assert plain_claude.index("[") == plain_codex.index("[")
        assert plain_claude.index("[", plain_claude.index("[") + 1) == plain_codex.index(
            "[", plain_codex.index("[") + 1
        )


def main() -> int:
    if "--self-check" in sys.argv[1:]:
        self_check()
        return 0
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    print(render_status(parse_stdin(), codex_home, time.time()), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
