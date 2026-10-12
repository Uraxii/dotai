import subprocess
import tempfile
import unittest
from pathlib import Path


CHECK = Path(__file__).resolve().parents[1] / 'check-plan.mjs'
RULE = (
    'Tests alone are not sufficient verification. A PR is verified only '
    'when its unit, live, and perf boxes are all checked.'
)


def plan(wake: str) -> str:
    lanes = '\n'.join(
        f'- [ ] Lane {n}. Drive the app. Save `lane-{n}.png`. Pass when ready.'
        for n in range(1, 11)
    )
    return f'''# Verify the app

## How to read this

One box is one unit of work. Each box names the evidence.
Check a box only when its evidence exists.
Use `playbooks/autopilot-stack.md`.
{RULE}

## Program checklist

### Arm the program

- [ ] Read `git show origin/main:playbooks/autopilot-stack.md`.
- [ ] {wake} Send a status message after a change.

### Spawn owners

- [ ] Spawn the owner.

### PR mechanics

- [ ] Open the PR.

### Verdict and merge

- [ ] Obtain the verdict.

### Boot recipe

- [ ] Launch the app.

## Verify the app

**Depends on.** None.

**Files.**

- [ ] Edit `app.py`.

**Build.**

- [ ] Build the app.

**You see.**

- [ ] The app starts.

**Verify, unit.** {RULE}

- [ ] Run tests.

**Verify, live.** {RULE} Ten lanes on `inherit-parent` at the PR head.

{lanes}

**Verify, perf.** {RULE}

- [ ] Metric. Startup seconds.
- [ ] Probe. Run startup.
- [ ] Baseline. Record startup.
- [ ] Rule. No slowdown.

**Review gate.** None.

**Merge.**

- [ ] Wait for approval.

## Close the program

- [ ] Report the result.

## Appendix A. Prototype evidence

The app starts.
'''


class PlanWakeTests(unittest.TestCase):
    def run_check(self, wake: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'app-plan.md'
            path.write_text(plan(wake))
            return subprocess.run(
                ['node', str(CHECK), str(path)],
                text=True, capture_output=True,
            )

    def test_supported_hourly_wake_passes(self) -> None:
        result = self.run_check('Arm an hourly scheduler or active-session loop.')
        self.assertEqual(0, result.returncode, result.stderr)

    def test_missing_cadence_fails(self) -> None:
        result = self.run_check('Run when convenient.')
        self.assertEqual(1, result.returncode)
        self.assertIn('Program checklist lacks "hourly"', result.stderr)


if __name__ == '__main__':
    unittest.main()
