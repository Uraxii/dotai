#!/usr/bin/env python3
"""Abandon one Orchestrate unit bead and pause its dependents.

Reads the unit, its blockers, and its dependents from bd, plans only the
writes the store still lacks, and runs them in order:

1. Take the unit's claim from whoever holds it.
2. Defer each open or in-progress dependent, which keeps it out of
   `bd ready`, drops its worker's lease, and refuses any new claim.
3. Resolve each open gate on the unit.
4. Remove the unit's dependency on each upstream unit.
5. Set `stage=abandoned` and close the unit.

A rerun reads the store again, so it skips every write that already landed
and changes nothing once the unit is abandoned. A failed run is resumed by
running it again.

    abandon_unit.py <unit id> --reason "<why>"

Run it with BEADS_ACTOR set to the coordinator's actor. It prints each bd
command it runs, then each dependent's worker actor, so the coordinator can
stop those agents. Python standard library only. `bd` must be on PATH.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass

CLOSED = "closed"
DEFERRED = "deferred"
IN_PROGRESS = "in_progress"
GATE = "gate"
ABANDONED_LABEL = "stage:abandoned"


class AbandonRefused(Exception):
    pass


@dataclass(frozen=True)
class Bead:
    id: str
    status: str
    issue_type: str
    assignee: str
    labels: frozenset[str]

    @classmethod
    def parse(cls, record: dict) -> Bead:
        return cls(id=record["id"], status=record["status"],
                   issue_type=record.get("issue_type", "task"),
                   assignee=record.get("assignee") or "",
                   labels=frozenset(record.get("labels") or ()))


@dataclass(frozen=True)
class UnitLinks:
    unit: Bead
    blockers: tuple[Bead, ...]
    dependents: tuple[Bead, ...]

    @property
    def gates(self) -> tuple[Bead, ...]:
        return tuple(b for b in self.blockers if b.issue_type == GATE)

    @property
    def upstream_units(self) -> tuple[Bead, ...]:
        return tuple(b for b in self.blockers if b.issue_type != GATE)


def plan(links: UnitLinks, actor: str, reason: str) -> list[list[str]]:
    """Return the bd argv lists that move `links` to the abandoned end state.

    Each write is planned only when the store lacks its effect, so planning
    against an abandoned unit returns an empty list.
    """
    unit = links.unit
    if unit.status == CLOSED and ABANDONED_LABEL not in unit.labels:
        raise AbandonRefused(f"{unit.id} is closed but not abandoned")
    steps: list[list[str]] = []
    if unit.status != CLOSED and unit.assignee != actor:
        steps.append(["update", unit.id, "--assignee", actor,
                      "--status", IN_PROGRESS,
                      "--if-assignee", unit.assignee])
    steps += [["defer", d.id, "--reason", f"replan after {unit.id} abandoned"]
              for d in links.dependents if d.status not in (CLOSED, DEFERRED)]
    steps += [["gate", "resolve", g.id, "--reason", "unit abandoned"]
              for g in links.gates if g.status != CLOSED]
    steps += [["dep", "remove", unit.id, u.id] for u in links.upstream_units]
    if ABANDONED_LABEL not in unit.labels:
        steps.append(["set-state", unit.id, "stage=abandoned",
                      "--reason", reason])
    if unit.status != CLOSED:
        steps.append(["close", unit.id, "--reason", f"abandoned: {reason}"])
    return steps


def bd(*args: str) -> str:
    return subprocess.run(["bd", *args], text=True, capture_output=True,
                          check=True).stdout


def read_beads(*args: str) -> tuple[Bead, ...]:
    return tuple(Bead.parse(r) for r in json.loads(bd(*args, "--json")) or ())


def read_links(unit_id: str) -> UnitLinks:
    return UnitLinks(
        unit=read_beads("show", unit_id)[0],
        blockers=read_beads("dep", "list", unit_id, "-t", "blocks"),
        dependents=read_beads("dep", "list", unit_id, "--direction", "up",
                              "-t", "blocks"))


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("unit")
    parser.add_argument("--reason", required=True)
    args = parser.parse_args(arguments)
    actor = os.environ.get("BEADS_ACTOR")
    if not actor:
        parser.error("set BEADS_ACTOR to the coordinator's actor")
    try:
        links = read_links(args.unit)
        steps = plan(links, actor, args.reason)
        for step in steps:
            print(shlex.join(["bd", *step]))
            bd(*step)
    except AbandonRefused as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as failure:
        print(f"failed, rerun to resume: {failure.stderr.strip()}",
              file=sys.stderr)
        return 1
    if not steps:
        print(f"{args.unit} is already abandoned; nothing to change")
    for dependent in links.dependents:
        if dependent.assignee and dependent.status != CLOSED:
            print(f"paused {dependent.id}; stop worker {dependent.assignee}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
