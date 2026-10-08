"""Tests for the Orchestrate abandon chain.

The planner tests run anywhere. The store tests drive the real script against
a throwaway bd store in a temp dir and are skipped where bd is not on PATH,
which includes CI.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from abandon_unit import Bead, UnitLinks, plan

SCRIPT = Path(__file__).resolve().parent / "abandon_unit.py"
COORDINATOR = "coordinator"
UNIT_WORKER = "developer-unit"
DEPENDENT_WORKER = "developer-busy"
WHY = "two retries failed"


def bead(bead_id: str, status: str = "open", issue_type: str = "task",
         assignee: str = "", labels: tuple[str, ...] = ()) -> Bead:
    return Bead(bead_id, status, issue_type, assignee, frozenset(labels))


def held_unit() -> UnitLinks:
    return UnitLinks(
        unit=bead("u", "in_progress", assignee=UNIT_WORKER),
        blockers=(bead("g", issue_type="gate"), bead("up")),
        dependents=(bead("d-open"),
                    bead("d-busy", "in_progress", assignee=DEPENDENT_WORKER)))


class PlanTest(unittest.TestCase):
    def test_gate_on_the_unit_is_resolved_once_and_never_unlinked(self):
        steps = plan(held_unit(), COORDINATOR, WHY)
        self.assertEqual([s for s in steps if "g" in s],
                         [["gate", "resolve", "g", "--reason",
                           "unit abandoned"]])

    def test_in_progress_dependent_is_deferred(self):
        steps = plan(held_unit(), COORDINATOR, WHY)
        self.assertIn(["defer", "d-busy", "--reason",
                       "replan after u abandoned"], steps)

    def test_no_step_creates_a_gate(self):
        steps = plan(held_unit(), COORDINATOR, WHY)
        self.assertEqual([s for s in steps if s[:2] == ["gate", "create"]],
                         [])

    def test_unit_claimed_by_an_earlier_run_is_not_claimed_again(self):
        links = held_unit()
        claimed = UnitLinks(bead("u", "in_progress", assignee=COORDINATOR),
                               links.blockers, links.dependents)
        self.assertEqual([s for s in plan(claimed, COORDINATOR, WHY)
                          if s[0] == "update"], [])

    def test_abandoned_unit_plans_nothing(self):
        abandoned = UnitLinks(
            unit=bead("u", "closed", assignee=COORDINATOR,
                      labels=("stage:abandoned",)),
            blockers=(bead("g", "closed", issue_type="gate"),),
            dependents=(bead("d-open", "deferred"),
                        bead("d-busy", "deferred",
                             assignee=DEPENDENT_WORKER)))
        self.assertEqual(plan(abandoned, COORDINATOR, WHY), [])


class Store:
    def __init__(self, root: Path) -> None:
        self.root = root

    def env(self, actor: str) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("BEADS_", "BD_"))}
        env.update(BEADS_DIR=str(self.root / ".beads"), BEADS_ACTOR=actor,
                   BD_ACTOR=actor, BD_NON_INTERACTIVE="1")
        return env

    def run(self, *args: str, actor: str = COORDINATOR,
            check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, cwd=self.root, env=self.env(actor),
                              text=True, capture_output=True, check=check)

    def bd(self, *args: str, actor: str = COORDINATOR) -> str:
        return self.run("bd", *args, actor=actor).stdout

    def json(self, *args: str) -> list[dict]:
        return json.loads(self.bd(*args, "--json")) or []

    def status(self, bead_id: str) -> dict:
        return self.json("show", bead_id)[0]

    def create(self, title: str, *args: str) -> str:
        return self.bd("create", title, "--silent", *args).strip()

    def abandon(self) -> subprocess.CompletedProcess[str]:
        return self.run(sys.executable, str(SCRIPT), self.unit,
                        "--reason", WHY, check=False)

    def build_program(self) -> None:
        self.bd("init", "--non-interactive", "--skip-agents", "--skip-hooks",
                "--prefix", "t", "--quiet")
        epic = self.create("program", "-t", "epic")
        self.upstream = self.create("upstream", "--parent", epic)
        self.unit = self.create("unit to abandon", "--parent", epic)
        self.open_dependent = self.create("open dependent", "--parent", epic)
        self.busy_dependent = self.create("busy dependent", "--parent", epic)
        self.bd("dep", "add", self.unit, self.upstream)
        self.bd("dep", "add", self.open_dependent, self.unit)
        self.bd("dep", "add", self.busy_dependent, self.unit)
        self.bd("update", self.unit, "--claim", actor=UNIT_WORKER)
        self.bd("update", self.busy_dependent, "--claim",
                actor=DEPENDENT_WORKER)
        self.bd("gate", "create", "--type", "human", "--blocks", self.unit,
                "--reason", "which API?")


@unittest.skipIf(shutil.which("bd") is None, "bd is not on PATH")
class StoreTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory(prefix="abandon-unit-")
        self.addCleanup(tmp.cleanup)
        self.store = Store(Path(tmp.name))
        self.store.build_program()

    def assert_abandoned(self) -> None:
        store = self.store
        unit = store.status(store.unit)
        self.assertEqual((unit["status"], unit["close_reason"]),
                         ("closed", f"abandoned: {WHY}"))
        self.assertIn("stage:abandoned", unit["labels"])
        blockers = store.json("dep", "list", store.unit, "-t", "blocks")
        self.assertEqual([(b["issue_type"], b["status"]) for b in blockers],
                         [("gate", "closed")], "one gate, resolved once")
        self.assertEqual(store.status(store.upstream)["status"], "open")
        for dependent in (store.open_dependent, store.busy_dependent):
            self.assertEqual(store.status(dependent)["status"], "deferred")
        ready = {b["id"] for b in store.json("ready")}
        self.assertEqual(ready & {store.open_dependent, store.busy_dependent},
                         set(), "dependents stay out of bd ready")
        self.assertEqual(store.json("gate", "list"), [],
                         "no gate left for the human to answer")
        respawn = store.run("bd", "update", store.busy_dependent, "--claim",
                            actor=DEPENDENT_WORKER, check=False)
        self.assertNotEqual(respawn.returncode, 0,
                            "paused dependent refuses its worker's claim")

    def test_second_run_changes_nothing(self):
        first = self.store.abandon()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assert_abandoned()
        before = self.store.bd("export", "--all")
        second = self.store.abandon()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("nothing to change", second.stdout)
        self.assertNotIn("bd ", second.stdout)
        self.assertEqual(self.store.bd("export", "--all"), before)
        self.assert_abandoned()

    def test_rerun_after_a_partial_run_converges(self):
        self.store.bd("update", self.store.unit, "--assignee", COORDINATOR,
                      "--status", "in_progress",
                      "--if-assignee", UNIT_WORKER)
        self.store.bd("defer", self.store.busy_dependent)
        rerun = self.store.abandon()
        self.assertEqual(rerun.returncode, 0, rerun.stderr)
        self.assert_abandoned()


if __name__ == "__main__":
    unittest.main()
