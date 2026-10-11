#!/usr/bin/env python3
"""Prove that concurrent bd claims and closes on one store behave.

The beads work loop relies on two bd behaviors under concurrency:

- When several actors run `bd update <id> --claim` on one bead at once,
  exactly one wins and the rest exit non-zero.
- When several processes close different beads at once, every close lands.

Each run builds a throwaway store in a temp dir with its own BEADS_DIR and
races the commands for several rounds, because one lucky round proves little.
It exits 1 on the first failed check.

    check_bd_concurrency.py [--rounds N]

Python standard library only. `bd` must be on PATH.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ROUNDS = 10
CLOSERS = 8
COORDINATOR = "coordinator"
STORE_ENV_PREFIXES = ("BEADS_", "BD_")


class CheckFailed(Exception):
    pass


@dataclass(frozen=True)
class Store:
    root: Path

    def env(self, actor: str) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(STORE_ENV_PREFIXES)}
        env.update(BEADS_DIR=str(self.root / ".beads"), BEADS_ACTOR=actor,
                   BD_ACTOR=actor, BD_NON_INTERACTIVE="1")
        return env

    def spawn(self, actor: str, *args: str) -> subprocess.Popen[str]:
        return subprocess.Popen(["bd", *args], cwd=self.root,
                                env=self.env(actor), text=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

    def run(self, *args: str) -> str:
        process = self.spawn(COORDINATOR, *args)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise CheckFailed(f"bd {' '.join(args)} exited "
                              f"{process.returncode}: {stderr.strip()}")
        return stdout

    def create(self, title: str) -> str:
        return self.run("create", title, "--silent").strip()

    def show(self, *ids: str) -> dict[str, dict]:
        issues = json.loads(self.run("show", *ids, "--json"))
        return {issue["id"]: issue for issue in issues}


def race(processes: dict[str, subprocess.Popen[str]]) -> dict[str, int]:
    return {key: process.wait() for key, process in processes.items()}


def check_claim_race(store: Store, round_number: int, racers: int) -> None:
    bead = store.create(f"claim race {racers} round {round_number}")
    actors = [f"racer-{index}" for index in range(racers)]
    exits = race({actor: store.spawn(actor, "update", bead, "--claim")
                  for actor in actors})
    winners = [actor for actor, code in exits.items() if code == 0]
    if len(winners) != 1:
        raise CheckFailed(f"{racers} actors claimed {bead}: {len(winners)} "
                          f"exited 0 ({winners}), expected exactly 1")
    issue = store.show(bead)[bead]
    if issue.get("assignee") != winners[0] or issue["status"] != "in_progress":
        raise CheckFailed(f"{bead} winner {winners[0]} but bead shows "
                          f"assignee {issue.get('assignee')!r}, "
                          f"status {issue['status']!r}")


def check_close_race(store: Store, round_number: int) -> None:
    beads = [store.create(f"close race round {round_number} bead {index}")
             for index in range(CLOSERS)]
    exits = race({bead: store.spawn(f"closer-{index}", "close", bead,
                                    "--reason", f"closed by closer-{index}")
                  for index, bead in enumerate(beads)})
    failed = [bead for bead, code in exits.items() if code != 0]
    if failed:
        raise CheckFailed(f"{len(failed)} of {CLOSERS} closes exited "
                          f"non-zero: {failed}")
    issues = store.show(*beads)
    lost = [bead for index, bead in enumerate(beads)
            if issues[bead]["status"] != "closed"
            or issues[bead].get("close_reason") != f"closed by closer-{index}"]
    if lost:
        raise CheckFailed(f"{len(lost)} of {CLOSERS} closes exited 0 but did "
                          f"not land: {lost}")


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    rounds = parser.parse_args(arguments).rounds
    checks = [
        ("2 actors race --claim on one bead",
         lambda store, n: check_claim_race(store, n, 2)),
        (f"{CLOSERS} processes close {CLOSERS} beads at once",
         check_close_race),
        ("8 actors race --claim on one bead",
         lambda store, n: check_claim_race(store, n, 8)),
    ]
    with tempfile.TemporaryDirectory(prefix="bd-concurrency-") as root:
        store = Store(Path(root))
        store.run("init", "--non-interactive", "--skip-agents",
                  "--skip-hooks", "--prefix", "race", "--quiet")
        print(store.run("--version").strip())
        for name, check in checks:
            try:
                for round_number in range(1, rounds + 1):
                    check(store, round_number)
            except CheckFailed as failure:
                print(f"FAIL {name}, round {round_number}: {failure}")
                return 1
            print(f"ok   {name}: {rounds} of {rounds} rounds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
