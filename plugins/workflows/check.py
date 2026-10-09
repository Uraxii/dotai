"""Validate every workflow and playbook. Run: uv run --with jsonschema --with pyyaml plugins/workflows/check.py"""
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).parent
GRID_POINTS = {1, 2, 3, 5, 8, 13}
SCHEMA = {k: Draft202012Validator(yaml.safe_load((ROOT / f"schema/{k}.schema.yaml").read_text())) for k in ("workflow", "playbook")}


def load(kind):
    return {p: yaml.safe_load(p.read_text()) for p in sorted((ROOT / f"{kind}s").glob("*.yaml"))}


def errors(workflows, playbooks):
    for kind, docs in (("workflow", workflows), ("playbook", playbooks)):
        for path, doc in docs.items():
            for e in SCHEMA[kind].iter_errors(doc):
                yield f"{path.name}: {e.json_path}: {e.message}"
            if doc.get("name") != path.stem:
                yield f"{path.name}: name must match the file name"
    names = {d["name"] for d in workflows.values()}
    for path, wf in workflows.items():
        loop = wf.get("loop")
        if loop and loop["back_to"] not in {s["id"] for s in wf["steps"]}:
            yield f"{path.name}: loop.back_to {loop['back_to']!r} is not a step id"
    covered = {}
    for path, pb in playbooks.items():
        for item in pb["chain"]:
            for ref in item["loop"]["do"] if isinstance(item, dict) else [item]:
                if ref not in names:
                    yield f"{path.name}: unknown workflow {ref!r}"
        for pt in pb["when"]["points"]:
            key = (pb["when"]["task"], pt)
            if key in covered:
                yield f"{path.name}: {key} already covered by {covered[key]}"
            covered[key] = path.name
    for task in sorted({t for t, _ in covered}):
        for pt in sorted(GRID_POINTS - {p for t, p in covered if t == task}):
            yield f"{task}: no playbook for {pt} points"


if __name__ == "__main__":
    found = list(errors(load("workflow"), load("playbook")))
    print("\n".join(found) or "ok")
    sys.exit(1 if found else 0)
