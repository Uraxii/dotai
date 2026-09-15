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
import subprocess
import sys
import threading
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
# Rate limits Codex /status shows come only from the server (`codex app-server`),
# so a detached `--refresh-codex-limits` run caches them and rendering reads the file.
CACHE_PATH = Path.home() / ".cache" / "statusline" / "codex-rate-limits.json"
LOCK_PATH = CACHE_PATH.with_suffix(".lock")
CACHE_TTL_SECONDS = 300
# A failed refresh leaves its lock behind, so this is also the retry backoff.
LOCK_STALE_SECONDS = 60
REFRESH_TIMEOUT_SECONDS = 15
REFRESH_FLAG = "--refresh-codex-limits"
SPARK_LIMIT_ID = "codex_bengalfox"


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


def limits_snapshot(
    rate_limits: object, observed_at: datetime | None, now_epoch: float
) -> UsageSnapshot:
    windows = windows_from_rate_limits(rate_limits, now_epoch)
    return UsageSnapshot(
        context=UNKNOWN_WINDOW,
        five_hour=windows.get(FIVE_HOUR_MINUTES, UNKNOWN_WINDOW),
        weekly=windows.get(WEEKLY_MINUTES, UNKNOWN_WINDOW),
        observed_at=observed_at,
    )


def codex_snapshot(event: Mapping[str, object], now_epoch: float) -> UsageSnapshot:
    payload = as_mapping(event.get("payload"))
    observed_at = parse_timestamp(event.get("timestamp"))
    return limits_snapshot(payload.get("rate_limits"), observed_at, now_epoch)


def cache_from_response(response: Mapping[str, object], fetched_at: float) -> dict[str, object]:
    """Keep only per-pool windows from `account/rateLimits/read`, in rollout field names.

    Allow-listed on purpose: the response also carries the account id.
    """
    pools: dict[str, object] = {}
    for limit_id, pool in as_mapping(response.get("rateLimitsByLimitId")).items():
        pool_data = as_mapping(pool)
        rate_limits = {}
        for slot in ("primary", "secondary"):
            window = as_mapping(pool_data.get(slot))
            if window:
                rate_limits[slot] = {
                    "used_percent": window.get("usedPercent"),
                    "window_minutes": window.get("windowDurationMins"),
                    "resets_at": window.get("resetsAt"),
                }
        pools[str(limit_id)] = {
            "limit_name": pool_data.get("limitName"),
            "plan_type": pool_data.get("planType"),
            "rate_limits": rate_limits,
        }
    return {"fetched_at": fetched_at, "pools": pools}


def spark_pool(cache: Mapping[str, object]) -> Mapping[str, object]:
    pools = as_mapping(cache.get("pools"))
    for pool in pools.values():
        limit_name = as_mapping(pool).get("limit_name")
        if isinstance(limit_name, str) and "Spark" in limit_name:
            return as_mapping(pool)
    return as_mapping(pools.get(SPARK_LIMIT_ID))


def pool_snapshot(pool: object, fetched_at: object, now_epoch: float) -> UsageSnapshot:
    fetched_epoch = as_number(fetched_at)
    try:
        observed_at = None if fetched_epoch is None else datetime.fromtimestamp(fetched_epoch, UTC)
    except (OverflowError, OSError, ValueError):
        return UNKNOWN_SNAPSHOT
    if not windows_from_rate_limits(as_mapping(pool).get("rate_limits"), now_epoch):
        return UNKNOWN_SNAPSHOT
    return limits_snapshot(as_mapping(pool).get("rate_limits"), observed_at, now_epoch)


def read_cache(cache_path: Path) -> Mapping[str, object]:
    try:
        return as_mapping(json.loads(cache_path.read_text()))
    except (OSError, ValueError):
        return {}


def start_refresh(lock_path: Path, now_epoch: float) -> None:
    """Spawn one detached refresher; the lock it inherits keeps a second one from starting."""
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.close(os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        except FileExistsError:
            if now_epoch - lock_path.stat().st_mtime < LOCK_STALE_SECONDS:
                return
            # ponytail: unlink-then-create can let two racers both take a stale lock; harmless.
            lock_path.unlink(missing_ok=True)
            os.close(os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), REFRESH_FLAG],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        return


def fetch_rate_limits() -> Mapping[str, object]:
    requests = (
        {
            "id": 1,
            "method": "initialize",
            "params": {"clientInfo": {"name": "statusline", "version": "1"}},
        },
        {"method": "initialized"},
        {"id": 2, "method": "account/rateLimits/read"},
    )
    server = subprocess.Popen(
        ["codex", "app-server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    deadline = threading.Timer(REFRESH_TIMEOUT_SECONDS, server.kill)
    deadline.start()
    try:
        assert server.stdin is not None and server.stdout is not None
        # stdin stays open: the server exits on EOF before answering request 2.
        server.stdin.write("".join(json.dumps(request) + "\n" for request in requests))
        server.stdin.flush()
        for line in server.stdout:
            try:
                message = as_mapping(json.loads(line))
            except ValueError:
                continue
            if message.get("id") == 2:
                return as_mapping(message.get("result"))
        return {}
    finally:
        deadline.cancel()
        server.kill()
        server.wait()


def refresh_codex_limits(cache_path: Path, lock_path: Path) -> int:
    try:
        cache = cache_from_response(fetch_rate_limits(), time.time())
        if not cache["pools"]:
            return 1
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = cache_path.with_suffix(".tmp")
        temporary_path.write_text(json.dumps(cache, indent=1))
        os.replace(temporary_path, cache_path)
        lock_path.unlink(missing_ok=True)
        return 0
    except (OSError, ValueError, subprocess.SubprocessError):
        return 1


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


def observed_epoch(snapshot: UsageSnapshot) -> float:
    return snapshot.observed_at.timestamp() if snapshot.observed_at else 0.0


def render_status(
    input_data: Mapping[str, object], codex_home: Path, cache_path: Path, now_epoch: float
) -> str:
    now = datetime.fromtimestamp(now_epoch, UTC)
    user_host = f"{DIM}{getpass.getuser()}@{socket.gethostname().split('.')[0]}{RESET}"
    first_parts = [user_host, battery_status(), tokens_per_minute(input_data)]
    line_one = "  ".join(part for part in first_parts if part)
    cache = read_cache(cache_path)
    fetched_at = as_number(cache.get("fetched_at"))
    if fetched_at is None or now_epoch - fetched_at > CACHE_TTL_SECONDS:
        start_refresh(cache_path.with_suffix(".lock"), now_epoch)
    rollout_codex = codex_usage_snapshot(codex_home, now_epoch)
    server_codex = pool_snapshot(as_mapping(cache.get("pools")).get("codex"), fetched_at, now_epoch)
    # Server data beats an older rollout; ties keep the rollout.
    codex = max(rollout_codex, server_codex, key=observed_epoch)
    spark = pool_snapshot(spark_pool(cache), fetched_at, now_epoch)
    claude_line = snapshot_line("claude", claude_snapshot(input_data))
    codex_line = snapshot_line(
        "codex", codex, age_suffix(codex.observed_at, now), include_context=False
    )
    spark_line = snapshot_line(
        "spark", spark, age_suffix(spark.observed_at, now), include_context=False
    )
    return "\n".join((line_one, claude_line, codex_line, spark_line))


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

    def server_window(used: int, minutes: int, resets_at: float) -> dict[str, float]:
        return {"usedPercent": used, "windowDurationMins": minutes, "resetsAt": resets_at}

    response = {
        "accountId": "secret-account",
        "rateLimitsByLimitId": {
            "codex": {
                "limitName": None,
                "primary": server_window(52, WEEKLY_MINUTES, now + 10),
                "secondary": None,
            },
            "codex_other_id": {
                "limitName": "GPT-5.3-Codex-Spark",
                "primary": server_window(90, FIVE_HOUR_MINUTES, now - 1),
                "secondary": server_window(25, WEEKLY_MINUTES, now + 10),
            },
        },
    }
    cache = cache_from_response(response, now - 30)
    assert "secret-account" not in json.dumps(cache)
    spark = pool_snapshot(spark_pool(cache), cache["fetched_at"], now)
    assert spark.five_hour.remaining_percent == 100, "expired window shows 100%"
    assert spark.weekly.remaining_percent == 75
    server_codex = pool_snapshot(cache["pools"]["codex"], cache["fetched_at"], now)
    assert server_codex.weekly.remaining_percent == 48
    assert server_codex.five_hour.remaining_percent is None
    by_id = {"pools": {SPARK_LIMIT_ID: {"limit_name": None, "rate_limits": {}}}}
    assert spark_pool(by_id) is by_id["pools"][SPARK_LIMIT_ID]
    assert pool_snapshot("garbage", "garbage", now) == UNKNOWN_SNAPSHOT
    nan_window = {"rate_limits": {"primary": {"window_minutes": float("nan")}}}
    assert pool_snapshot(nan_window, 1e300, now) == UNKNOWN_SNAPSHOT
    cases = (
        (UsageSnapshot(UsageWindow(25), UsageWindow(75), UsageWindow(51)), False),
        (UNKNOWN_SNAPSHOT, False),
        (UsageSnapshot(UsageWindow(100), UsageWindow(100), UsageWindow(100)), False),
        (UsageSnapshot(UsageWindow(5), UsageWindow(5), UsageWindow(5)), True),
    )
    for snapshot, expect_warning in cases:
        claude_line = snapshot_line("claude", snapshot)
        codex_line = snapshot_line("codex", snapshot, include_context=False)
        spark_line = snapshot_line("spark", snapshot, include_context=False)
        if expect_warning:
            assert WARN in claude_line
            assert WARN in codex_line
        plain_claude, plain_codex, plain_spark = (
            re.sub(r"\x1b\[[0-9;]*m", "", line) for line in (claude_line, codex_line, spark_line)
        )
        assert "ctx" not in plain_codex
        assert "ctx" not in plain_spark
        bar_columns = {
            tuple(match.start() for match in re.finditer(r"\[", line))[:2]
            for line in (plain_claude, plain_codex, plain_spark)
        }
        assert len(bar_columns) == 1, bar_columns


def main() -> int:
    if "--self-check" in sys.argv[1:]:
        self_check()
        return 0
    if REFRESH_FLAG in sys.argv[1:]:
        return refresh_codex_limits(CACHE_PATH, LOCK_PATH)
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    print(render_status(parse_stdin(), codex_home, CACHE_PATH, time.time()), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
