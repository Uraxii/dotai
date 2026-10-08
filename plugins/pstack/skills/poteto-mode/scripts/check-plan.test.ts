import { afterAll, describe, expect, it } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const SCRIPT = join(import.meta.dir, "check-plan.mjs");
const PLAYBOOK = join(import.meta.dir, "../playbooks/multi-phase-plan.md");
const RULE =
  "Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.";

function playbookSkeleton(): string {
  const match = readFileSync(PLAYBOOK, "utf8").match(/^````markdown\n([\s\S]*?)^````$/m);
  if (!match) throw new Error(`${PLAYBOOK} has no markdown plan skeleton`);
  return match[1];
}

const SKELETON = playbookSkeleton();
const scratch = mkdtempSync(join(tmpdir(), "check-plan-"));
afterAll(() => rmSync(scratch, { recursive: true, force: true }));

interface CheckResult {
  readonly status: number | null;
  readonly stdout: string;
  readonly stderr: string;
}

let written = 0;
function checkPlan(plan: string): CheckResult {
  const file = join(scratch, `plan-${++written}.md`);
  writeFileSync(file, plan);
  const result = spawnSync("node", [SCRIPT, file], { encoding: "utf8", timeout: 5000 });
  return { status: result.status, stdout: result.stdout, stderr: result.stderr };
}

function edit(plan: string, from: string | RegExp, to: string): string {
  const edited = plan.replace(from, to);
  if (edited === plan) throw new Error(`the plan skeleton no longer contains ${from}`);
  return edited;
}

interface Breakage {
  readonly name: string;
  readonly problem: string;
  readonly mutate: (plan: string) => string;
}

const PROGRAM_HEADINGS = ["Arm the program", "Spawn owners", "PR mechanics", "Verdict and merge", "Boot recipe"];

const BREAKAGES: readonly Breakage[] = [
  {
    name: "the program epic marker is gone",
    problem: 'Program checklist lacks "program epic"',
    mutate: (plan) => edit(plan, /program epic/g, "program bead"),
  },
  {
    name: "the installed plugin marker is gone",
    problem: 'Program checklist lacks "installed plugin"',
    mutate: (plan) => edit(plan, /installed plugin/g, "plugin"),
  },
  {
    name: "the 30-minute tick is gone",
    problem: 'Program checklist lacks "/30[- ]minute/"',
    mutate: (plan) => edit(plan, "30-minute audit tick", "hourly audit tick"),
  },
  {
    name: "the status message is gone",
    problem: 'Program checklist lacks "status message"',
    mutate: (plan) => edit(plan, "status message", "status note"),
  },
  ...PROGRAM_HEADINGS.map((heading) => ({
    name: `the "${heading}" task is renamed`,
    problem: `Program checklist lacks "### ${heading}" in order`,
    mutate: (plan: string) => edit(plan, `### ${heading}`, "### Something else"),
  })),
  {
    name: "a program task has no box",
    problem: "Spawn owners has no box",
    mutate: (plan) => edit(plan, /(### Spawn owners\n\n)[\s\S]*?(?=### PR mechanics)/, "$1Owners spawn.\n\n"),
  },
  ...[
    "One box is one unit of work",
    "names the evidence",
    "Check a box only when its evidence exists",
    "playbooks/",
    RULE,
  ].map((marker) => ({
    name: `How to read this loses "${marker.slice(0, 30)}"`,
    problem: `How to read this lacks "${marker}"`,
    mutate: (plan: string) => edit(plan, marker, "Read the plan."),
  })),
  {
    name: "the intro runs ten lines",
    problem: "intro is 10 lines, under ten required",
    mutate: (plan) => edit(plan, /^(# .*\n)/m, `$1${"Intro line.\n".repeat(9)}`),
  },
  {
    name: "there is no H1",
    problem: "no H1 title",
    mutate: (plan) => edit(plan, /^# /m, "Title "),
  },
  {
    name: "a sub-block is renamed",
    problem: "sub-blocks are [Depends on., Files., Build., You see., Verify, unit., Verify, live., Verify, perf., Review gate.]",
    mutate: (plan) => edit(plan, "**Merge.**", "**Land.**"),
  },
  {
    name: "Depends on names nothing",
    problem: "Depends on names nothing",
    mutate: (plan) => edit(plan, "**Depends on.** <PR id, or None.>", "**Depends on.**"),
  },
  {
    name: "Build has no box",
    problem: "Build. has no box",
    mutate: (plan) => edit(plan, "- [ ] <One change. Name the symbol and the file.>", "One change."),
  },
  {
    name: "a verify block skips the rule",
    problem: "Verify, perf. does not open with the rule",
    mutate: (plan) => edit(plan, `**Verify, perf.** ${RULE}`, "**Verify, perf.** Measure it."),
  },
  {
    name: "the live block drops the lane model",
    problem: "Verify, live lacks",
    mutate: (plan) => edit(plan, "Ten lanes on the configured `swarm workers` model at the PR head", "Some lanes"),
  },
  {
    name: "lane 10 is missing",
    problem: "lanes are [1,2,3,4,5,6,7,8,9], expected 1 to 10",
    mutate: (plan) => edit(plan, /^- \[ \] Lane 10\..*\n/m, ""),
  },
  {
    name: "a live box is not a lane",
    problem: "live box is not a lane",
    mutate: (plan) => edit(plan, "- [ ] Lane 3.", "- [ ] Third."),
  },
  {
    name: "a lane names no screenshot",
    problem: "lane 4 names no screenshot",
    mutate: (plan) => edit(plan, /(Lane 4\. <Scenario\.> )Save `<slug>\.png`\. /, "$1"),
  },
  {
    name: "a lane has no pass predicate",
    problem: "lane 5 has no pass predicate",
    mutate: (plan) => edit(plan, /(Lane 5\. .*?) Pass when <predicate>\./, "$1"),
  },
  {
    name: "a perf box is renamed",
    problem: "perf boxes are [Metric., Probe., Trunk., Rule.]",
    mutate: (plan) => edit(plan, "- [ ] Baseline.", "- [ ] Trunk."),
  },
  ...["screenshot", "video", "operator"].map((word) => ({
    name: `the review gate drops "${word}"`,
    problem: `Review gate lacks "${word}"`,
    mutate: (plan: string) => {
      const gate = plan.match(/\*\*Review gate\.\*\*[\s\S]*?(?=\*\*Merge\.\*\*)/);
      if (!gate) throw new Error("the plan skeleton has no Review gate block");
      return edit(plan, gate[0], gate[0].replaceAll(word, "thing"));
    },
  })),
  {
    name: "a None review gate keeps its boxes",
    problem: "Review gate says None but has boxes",
    mutate: (plan) => edit(plan, "**Review gate.** The operator reviews before merge.", "**Review gate.** None. X is not review-gated."),
  },
  {
    name: "Close the program is missing",
    problem: 'no "## Close the program" section',
    mutate: (plan) => edit(plan, "## Close the program", "## Wrap up"),
  },
  {
    name: "Close the program has no box",
    problem: "Close the program has no box",
    mutate: (plan) => edit(plan, /(## Close the program\n\n)[\s\S]*?(?=## Appendix A)/, "$1Done.\n\n"),
  },
  {
    name: "no PR section sits between the checklist and the close",
    problem: "no PR sections between Program checklist and Close the program",
    mutate: (plan) => edit(plan, /^## <Task as a verb phrase>[\s\S]*?(?=^## Close the program)/m, ""),
  },
  {
    name: "a section after the close is not an appendix",
    problem: '"## Notes" after Close the program is not an appendix',
    mutate: (plan) => `${plan}\n## Notes\n\nMore.\n`,
  },
  {
    name: "the prototype evidence appendix is missing",
    problem: 'no "## Appendix ... Prototype evidence" section',
    mutate: (plan) => edit(plan, "## Appendix A. Prototype evidence", "## Appendix A. Spikes"),
  },
  {
    name: "prose carries a long dash",
    problem: "long dash",
    mutate: (plan) => `${plan}\nA claim — and an aside.\n`,
  },
  {
    name: "prose carries a curly quote",
    problem: "curly quote",
    mutate: (plan) => `${plan}\nShe said “no”.\n`,
  },
  {
    name: "prose carries a mid-sentence colon",
    problem: "mid-sentence colon",
    mutate: (plan) => `${plan}\nOne thing: another.\n`,
  },
];

describe("check-plan.mjs", () => {
  it("passes the plan skeleton in the multi-phase-plan playbook", () => {
    const result = checkPlan(SKELETON);
    expect(result.status, result.stderr).toBe(0);
    expect(result.stdout).toContain("1 PR sections, 0 problems");
  });

  it("ignores long dashes, curly quotes, and colons inside a code fence", () => {
    const result = checkPlan(`${SKELETON}\n\`\`\`\nA — b “c”: d\n\`\`\`\n`);
    expect(result.status, result.stderr).toBe(0);
  });

  for (const breakage of BREAKAGES) {
    it(`fails when ${breakage.name}`, () => {
      const result = checkPlan(breakage.mutate(SKELETON));
      expect(result.status).toBe(1);
      expect(result.stderr).toContain(breakage.problem);
    });
  }
});
