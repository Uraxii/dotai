"""The code-quality guideline hook, run through its wrapper the way a harness
runs it: payload on stdin, one JSON object or nothing on stdout. Guideline
files are fixtures written here, and ruff and eslint are stubs, so the
result does not depend on the real guidelines folder or on installed tools.

Usage: python3 plugins/pstack/hooks/tests/guidelines.test.py (Python 3.11+)
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
HOOK = PLUGIN / "hooks" / "guidelines.py"
ENGINE = PLUGIN / "skills" / "principle-code-quality" / "scripts" / "guideline_hook.py"
WORK = Path(tempfile.mkdtemp())
FIXTURES = WORK / "guidelines"
BIN = WORK / "bin"
EMPTY = WORK / "empty"
for directory in (FIXTURES, BIN, EMPTY):
    directory.mkdir(parents=True)
BASE_ENV = {
    **os.environ, "WORK": str(WORK), "CLAUDE_PLUGIN_ROOT": str(PLUGIN),
    "CLAUDE_PLUGIN_DATA": str(WORK / "data"),
    "PSTACK_GUIDELINES_DIR": str(FIXTURES), "PATH": str(BIN),
}
for name in ("PLUGIN_DATA", "PSTACK_GUIDELINE_DATA"):
    BASE_ENV.pop(name, None)

passed = failed = 0


def expect_equal(name, expected, actual):
    global passed, failed
    if expected == actual:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL  {name}\n    expected: {expected}\n    actual:   {actual}")


def expect_contains(name, needle, haystack):
    global passed, failed
    if needle in haystack:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL  {name}\n    expected to contain: {needle}\n    actual: {haystack}")


def expect_lacks(name, needle, haystack):
    expect_equal(name, False, needle in haystack)


def expect_json(name, expected, actual):
    try:
        actual = json.loads(actual)
    except ValueError:
        actual = f"not json: {actual}"
    expect_equal(name, expected, actual)


def guideline(file, body, *keys, folder=FIXTURES):
    (folder / file).write_text("---\n" + "".join(f"{k}\n" for k in keys) + f"---\n{body}\n")


ONE_FOR = "Use at most one `for` clause per comprehension. Write a flattening comprehension as an explicit `for` loop that names each intermediate value."
NESTED_CALL = "Inside a comprehension, do not pass a call's result straight into another call. Bind the inner result to a name in an explicit `for` loop."
DATACLASS = "Model a record with a `@dataclass`, not a `dict` with fixed string keys."
NO_STAR = "Import names explicitly; do not use `from module import *`."
NO_VAR = "Declare bindings with `const`, or `let` when reassigned; never `var`."
guideline("py-comprehension-one-for.md", ONE_FOR, "id: py.comprehension.one-for",
          "languages: python", "scope: contextual", "severity: block", "enabled: true",
          "detectors: code_quality:CQ001", "keywords: list comprehension, flatten")
guideline("py-comprehension-no-nested-call.md", NESTED_CALL, "id: py.comprehension.no-nested-call",
          "languages: python", "scope: contextual", "severity: warn", "enabled: true",
          "detectors: code_quality:CQ002")
guideline("py-error-no-assert-in-prod.md",
          "Do not use `assert` for runtime checks in production code; raise an exception instead.",
          "id: py.error.no-assert-in-prod", "languages: python", "scope: contextual",
          "severity: warn", "enabled: true", "detectors: ruff:S101", "keywords: assert",
          "exclude: tests/*, test_*.py, *_test.py, conftest.py")
guideline("py-import-no-star.md", NO_STAR, "id: py.import.no-star", "languages: python",
          "scope: contextual", "severity: block", "enabled: true", "detectors: ruff:F403")
guideline("py-logging-no-print.md", "Use the logging module, not print.", "id: py.logging.no-print",
          "languages: python", "scope: contextual", "severity: warn", "enabled: false",
          "detectors: ruff:T201")
guideline("py-data-dataclass-over-dict.md", DATACLASS, "id: py.data.dataclass-over-dict",
          "languages: python", "scope: global", "severity: warn", "enabled: true", "detectors:")
guideline("ts-binding-no-var.md", NO_VAR, "id: ts.binding.no-var",
          "languages: typescript, javascript", "scope: contextual", "severity: block",
          "enabled: true", "detectors: eslint:no-var")

# The hook sees only these programs: no installed ruff or eslint.
(BIN / "python3").symlink_to(sys.executable)
RUFF_STUB = f"""#!{sys.executable}
import os, sys, time
if sys.argv[1:] == ["--version"]:
    print(os.environ.get("RUFF_VERSION", "ruff 0.16.9"))
    sys.exit(0)
with open(os.path.join(os.environ["WORK"], "ruff.args"), "a") as args:
    args.write(" ".join(sys.argv[1:]) + "\\n")
with open(os.path.join(os.environ["WORK"], "ruff.stdin"), "wb") as text:
    text.write(sys.stdin.buffer.read())
time.sleep(float(os.environ.get("RUFF_SLEEP") or 0))
if os.environ.get("RUFF_STDERR"):
    print(os.environ["RUFF_STDERR"], file=sys.stderr)
print(os.environ.get("RUFF_JSON") or "[]")
"""
ESLINT_STUB = f"""#!{sys.executable}
import os, sys
if sys.argv[1:] == ["--version"]:
    print("v10.1.0")
    sys.exit(0)
if sys.argv[1:2] == ["--print-config"]:
    # As the Node resolve hook does: the config files, then $ESLINT_LOADED.
    import glob
    out = os.environ.get("PSTACK_ESLINT_LOADED")
    # ESLint looks for every flat config name (a `?` line).
    loaded = ["?" + os.path.realpath(p) for p in glob.glob(os.path.join(os.getcwd(), "eslint.config.*"))]
    loaded += [os.path.realpath(p) for p in glob.glob(os.path.join(os.getcwd(), ".eslintrc*"))]
    loaded += [name[0] * (name[0] == "?") + os.path.realpath(os.path.join(os.getcwd(), name.lstrip("?"))) for name in
               os.environ.get("ESLINT_LOADED", "").split(os.pathsep) if name]
    if out and os.environ.get("ESLINT_LOADED") != "none":
        open(out, "w").write("\\n".join(loaded))
    sys.exit(0)
with open(os.path.join(os.environ["WORK"], "eslint.args"), "a") as args:
    args.write(" ".join(sys.argv[1:]) + "\\n")
with open(os.path.join(os.environ["WORK"], "eslint.cwd"), "w") as cwd:
    cwd.write(os.getcwd())
with open(os.path.join(os.environ["WORK"], "eslint.env"), "w") as env:
    env.write(os.environ.get("ESLINT_USE_FLAT_CONFIG", ""))
# Empty source has no findings, as in ESLint.
source = sys.stdin.read()
found = source.strip() and os.environ.get("ESLINT_ONLY", "") in source
print(found and os.environ.get("ESLINT_JSON") or '[{{"messages":[]}}]')
"""


def install_stub(name, text):
    (BIN / name).write_text(text)
    (BIN / name).chmod(0o755)


install_stub("ruff", RUFF_STUB)
install_stub("eslint", ESLINT_STUB)

PAGES = "def pages(paths):\n    return tuple(page for path in paths for page in parse_page(_read(path)))\n"
EXPLICIT_LOOP = """def pages(paths):
    found = []
    for path in paths:
        text = _read(path)
        found.extend(parse_page(text))
    print(len(found))
    return tuple(found)
"""
OVERRIDE = "Project standards, configs and lints override these defaults."
BLOCKED = f"Blocked: this edit adds code that breaks a block guideline. Fix it, then retry the edit.\n{OVERRIDE}"


def announce(*ids):
    noun = "guideline" if len(ids) == 1 else "guidelines"
    return ("Start your next message to the user with this line exactly as written, on its own first line and with "
            "nothing appended to it, so the developer can see which pstack code-quality guidelines were issued. This "
            "printed line is all they need about guidelines, so there's no need to add, anywhere in your reply, which "
            f"ones applied: pstack code quality: {', '.join(ids)} {noun} provided")


PAGES_REASON = f"""{BLOCKED}

{announce("py.comprehension.one-for", "py.comprehension.no-nested-call")}

[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:2
{ONE_FOR}

[py.comprehension.no-nested-call] warn: code_quality:CQ002 at pages.py:2
{NESTED_CALL}"""
GLOBALS_CONTEXT = f"""Code-quality guidelines (pstack):
{OVERRIDE}

{announce("py.data.dataclass-over-dict")}

[py.data.dataclass-over-dict] warn
{DATACLASS}"""
F403_ROW = '[{"code":"F403","location":{"row":1}}]'
FAILED_TEXT = "pstack guideline hook failed; code-quality guidelines were not checked for this call."
LOG = WORK / "data" / "guideline-state" / "errors.log"


class Case:
    """One project directory and session; holds the last hook result."""

    def __init__(self, session):
        self.session = session
        self.project = WORK / "projects" / session
        (self.project / "src").mkdir(parents=True)
        (self.project / "tests").mkdir()
        for args in ("ruff.args", "eslint.args"):
            (WORK / args).unlink(missing_ok=True)
        self.stdout, self.status = "", None

    def env(self, extra):
        return {**BASE_ENV, "CLAUDE_PROJECT_DIR": str(self.project), **extra}

    def run(self, command, stdin=b"", extra=None, timeout=None, cwd=None):
        if isinstance(stdin, str):
            stdin = stdin.encode()
        done = subprocess.run(command, input=stdin, capture_output=True, shell=isinstance(command, str), check=False,
                              env=self.env(extra or {}), timeout=timeout, cwd=cwd)
        self.stdout, self.status = done.stdout.decode("utf-8", "replace"), done.returncode
        return self

    def hook(self, payload, harness="claude", **extra):
        if not isinstance(payload, (str, bytes)):
            payload = json.dumps(payload)
        return self.run([sys.executable, str(HOOK), harness], payload, extra)

    def engine(self, *args, stdin=b"", cwd=None):
        return self.run([sys.executable, "-I", str(ENGINE), *args], stdin, cwd=cwd or self.project)

    def file(self, name, content):
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, newline="")
        return path

    def tool(self, event, tool, file, extra=None):
        return {"hook_event_name": event, "session_id": self.session, "cwd": str(self.project),
                "tool_name": tool, "tool_input": {"file_path": f"{self.project}/{file}", **(extra or {})}}

    def write(self, file, text, event="PreToolUse"):
        return self.tool(event, "Write", file, {"content": text})

    def prompt(self, text):
        return {"hook_event_name": "UserPromptSubmit", "session_id": self.session,
                "cwd": str(self.project), "prompt": text}

    def session_start(self, source):
        return {"hook_event_name": "SessionStart", "session_id": self.session,
                "cwd": str(self.project), "source": source}

    def patch(self, event, text):
        return {"hook_event_name": event, "session_id": self.session, "cwd": str(self.project),
                "tool_name": "apply_patch", "tool_input": {"command": text}}

    def output(self):
        try:
            value = json.loads(self.stdout)
        except ValueError:
            return {}
        return value if isinstance(value, dict) else {}

    def specific(self, key):
        return self.output().get("hookSpecificOutput", {}).get(key) or ""

    def decision(self):
        return self.specific("permissionDecision")

    def reason(self):
        return self.specific("permissionDecisionReason")

    def context(self):
        return self.specific("additionalContext")

    def message(self):
        return self.output().get("systemMessage")

    def args(self, tool="ruff"):
        path = WORK / f"{tool}.args"
        return path.read_text().rstrip("\n") if path.exists() else ""


def lines(*rows):
    return "".join(f"{row}\n" for row in rows)


c = Case("flattening")
c.hook(c.write("pages.py", PAGES))
expect_equal("a flattening comprehension is denied", "deny", c.decision())
expect_equal("the deny reason carries both findings and their guidance", PAGES_REASON, c.reason())
expect_equal("the deny exits 0", 0, c.status)
expect_equal("the user is not shown the deny twice", None, c.message())

c = Case("clean")
c.hook(c.write("pages.py", EXPLICIT_LOOP))
expect_equal("the explicit loop is not denied", "", c.decision())
expect_equal("the first Python touch delivers the global guideline", GLOBALS_CONTEXT, c.context())
c.hook(c.write("pages.py", EXPLICIT_LOOP))
expect_equal("a second clean write says nothing", "0:", f"{c.status}:{c.stdout}")
c.hook({**c.tool("PostToolUse", "Read", "pages.py"), "agent_id": "a1"})
expect_contains("a subagent gets its own delivery", "[py.data.dataclass-over-dict] warn", c.context())
c.hook(c.session_start("compact"))
expect_equal("compaction sends the globals again", GLOBALS_CONTEXT, c.context())
c.hook(c.tool("PostToolUse", "Read", "pages.py"))
expect_equal("a read after compaction says nothing", "", c.stdout)
state = WORK / "data" / "guideline-state" / "clean" / "main.json"
expect_equal("state files are private", "0o600", oct(state.stat().st_mode & 0o777))

c = Case("preexisting")
c.file("pages.py", PAGES)
c.hook(c.tool("PreToolUse", "Edit", "pages.py",
              {"old_string": "def pages(paths):", "new_string": "def pages(paths):  # noqa-free"}))
expect_equal("an edit that leaves an old violation is not denied", "", c.decision())
c.hook(c.tool("PostToolUse", "Edit", "pages.py"))
expect_contains("the old violation arrives as a warning after the write",
                "[py.comprehension.one-for] warn: code_quality:CQ001 at pages.py:2", c.context())

c = Case("adds")
c.file("pages.py", EXPLICIT_LOOP)
c.hook(c.tool("PreToolUse", "Edit", "pages.py", {
    "old_string": "    return tuple(found)", "new_string": "    return tuple(p for q in found for p in q)"}))
expect_equal("an edit that adds the violation is denied", "deny", c.decision())
expect_contains("the deny names the new line",
                "[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:7", c.reason())

c = Case("replace-all")
c.file("pages.py", "x = 1\nx = 1\n")
c.hook(c.tool("PreToolUse", "Edit", "pages.py", {
    "old_string": "x = 1", "new_string": "x = [a for b in c for a in b]", "replace_all": True}))
expect_equal("replace_all blocks each added line and announces the guideline once", f"""{BLOCKED}

{announce("py.comprehension.one-for")}

[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:1
{ONE_FOR}

[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:2 (guidance sent earlier)""", c.reason())

c = Case("refused")
c.file("pages.py", "x = 1\n")
c.hook(c.tool("PreToolUse", "Edit", "pages.py", {"old_string": "absent", "new_string": "y = [a for b in c for a in b]"}))
expect_contains("an edit whose text cannot be built is named",
                "Notice: did not check pages.py: could not build the text this edit leaves, so PostToolUse checks it",
                c.context())
expect_equal("and is not denied", "", c.decision())

c = Case("crlf")
c.file("pages.py", "def pages(paths):\r\n    return tuple(found)\r\n")
c.hook(c.tool("PreToolUse", "Edit", "pages.py", {
    "old_string": "def pages(paths):\n    return tuple(found)",
    "new_string": "def pages(paths):\n    return tuple(p for q in found for p in q)"}))
expect_contains("an LF edit to a CRLF file is applied and denied",
                "[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:2", c.reason())

c = Case("unreadable")
c.file("pages.py", b"x = 1\n\xff\n")
c.hook(c.tool("PreToolUse", "Edit", "pages.py", {"old_string": "x = 1", "new_string": "y = 2"}))
expect_contains("a file that is not UTF-8 is named",
                "Notice: did not check pages.py: it is not UTF-8 text, so PostToolUse checks it", c.context())
c.hook(c.tool("PostToolUse", "Edit", "pages.py"))
expect_contains("and named again after the write", "Notice: did not check pages.py: it is not UTF-8 text", c.context())
c.hook(c.write("pages.py", PAGES))
expect_equal("a Write over a file that is not UTF-8 does not deny", "", c.decision())
expect_contains("but is still checked, and its findings are warnings",
                "Notice: could not read the current pages.py: it is not UTF-8 text, so its findings are warnings.",
                c.context())
c.file("pages.py", "def invalid(\n")
c.hook(c.write("pages.py", PAGES))
expect_equal("a Write over a file the detector cannot parse does not deny", "", c.decision())
expect_contains("and says the block check was inconclusive",
                "Notice: code_quality could not check the current pages.py, so its findings in this edit are warnings.",
                c.context())
c.file("run", "#!/usr/bin/env python3\nx = 0\n")
c.hook(c.tool("PreToolUse", "Edit", "run", {"old_string": "not here", "new_string": "y = 1"}))
expect_contains("an unbuilt edit to an extensionless script is named",
                "Notice: did not check run: could not build the text this edit leaves", c.context())

c = Case("non-code")
for file, text, name in (
    ("notes.md", PAGES, "a non-code file says nothing"),
    ("main.go", "package main", "a language with no guidelines says nothing"),
    ("../outside.py", PAGES, "a file outside the project says nothing"),
    ("node_modules/pkg/pages.py", PAGES, "a vendored file says nothing"),
    ("build/pages.py", PAGES, "a file in a root build directory says nothing"),
):
    c.hook(c.write(file, text))
    expect_equal(name, "0:", f"{c.status}:{c.stdout}")
c.hook(c.write("src/app/build/pages.py", PAGES))
expect_equal("a nested build directory is checked", "deny", c.decision())
c.hook(c.write("bin/pages", "#!/usr/bin/env python3\n" + PAGES))
expect_equal("an extensionless file with a python shebang is checked", "deny", c.decision())

c = Case("multi-edit")
c.file("pages.py", "x = 1\n")
c.hook(c.tool("PreToolUse", "MultiEdit", "pages.py", {"edits": [
    {"old_string": "x = 1", "new_string": "y = 2"},
    {"old_string": "y = 2", "new_string": "y = [a for b in c for a in b]"}]}))
expect_contains("MultiEdit edits apply in order",
                "[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:1", c.reason())

c = Case("exclude")
c.hook(c.write("tests/test_app.py", "assert x\n"))
c.hook(c.write("src/app.py", "assert x\n"))
expect_equal("an excluded guideline's detector is not selected", (
    f"check --isolated --preview --line-length 80 --select F403 --output-format json --stdin-filename {c.project}/tests/test_app.py -\n"
    f"check --isolated --preview --line-length 80 --select F403,S101 --output-format json --stdin-filename {c.project}/src/app.py -"),
    c.args())

c = Case("disabled")
c.hook(c.write("src/app.py", 'print("x")\n'), RUFF_JSON='[{"code":"T201","location":{"row":1}}]')
expect_equal("a disabled guideline's detector is not selected",
             f"check --isolated --preview --line-length 80 --select F403,S101 --output-format json --stdin-filename {c.project}/src/app.py -",
             c.args())
expect_lacks("a disabled guideline is never delivered", "py.logging.no-print", c.stdout)

c = Case("project-default")
c.hook(c.write("src/app.py", "from os import *\n"), RUFF_JSON=F403_ROW)
expect_equal("with no project config the default rule blocks", f"""{BLOCKED}

{announce("py.import.no-star")}

[py.import.no-star] block: ruff:F403 at src/app.py:1
{NO_STAR}""", c.reason())

c = Case("project-ignores")
c.file("ruff.toml", '[lint]\nignore = ["F403"]\n')
c.file(".ruff.toml", "[lint]\n")
c.hook(c.write("src/app.py", "from os import *\n"), RUFF_JSON=F403_ROW)
expect_equal(".ruff.toml wins over ruff.toml, as in ruff", "deny", c.decision())
(c.project / ".ruff.toml").unlink()
c.hook(c.write("src/app.py", "from os import *\n"))
expect_equal("a rule the project ignores does not block", "", c.decision())
expect_lacks("a rule the project ignores gives no finding", "py.import.no-star", c.stdout)
expect_equal("ruff runs with the project config, without the ignored rule",
             f"check --verbose --force-exclude --preview --extend-select S101 --output-format json --stdin-filename {c.project}/src/app.py -",
             c.args().splitlines()[-1])
c.hook(c.write("src/dist/app.py", "assert x\n"), RUFF_JSON=F403_ROW,
       RUFF_STDERR='DEBUG Ignored path via `exclude`: "src/dist"')
expect_equal("a file ruff's config excludes does not deny", "", c.decision())
expect_contains("and the user is told ruff skipped it",
                "Notice: ruff skips this file under its exclude settings (the project's or ruff's defaults), so detectors ruff:F403, ruff:S101 did not run.",
                c.context())
c.hook(c.tool("PostToolUse", "Write", "src/app.py"))
expect_lacks("the ignored rule stays quiet after the write", "py.import.no-star", c.stdout)
two = WORK / "two-detectors"
shutil.copytree(FIXTURES, two)
no_star = two / "py-import-no-star.md"
no_star.write_text(no_star.read_text().replace("detectors: ruff:F403\n", "detectors: ruff:F403, code_quality:CQ001\n"))
(two / "py-comprehension-one-for.md").unlink()
c.hook(c.write("src/two.py", "x = [a for b in c for a in b]\n"), PSTACK_GUIDELINES_DIR=str(two))
expect_contains("an ignored detector leaves the guideline's other detectors on",
                "[py.import.no-star] block: code_quality:CQ001 at src/two.py:1", c.reason())
expect_lacks("ruff is not asked to select the ignored detector", "F403", c.args().splitlines()[-1])

c = Case("project-pyproject")
c.file("pyproject.toml", '[tool.ruff.lint.per-file-ignores]\n"src/*" = ["F403"]\n')
c.hook(c.write("src/app.py", "from os import *\n"), RUFF_JSON="[]")
expect_contains("ruff applies the project's per-file ignores itself, so the hook still selects the code",
                "F403", c.args().splitlines()[-1])
expect_equal("a per-file ignore in pyproject.toml does not block", "", c.decision())
c.hook(c.write("lib.py", "from os import *\n"), RUFF_JSON=F403_ROW)
expect_equal("the same rule still blocks outside the ignored path", "deny", c.decision())

c = Case("editorconfig")
c.file(".editorconfig", "[*]\nmax_line_length = 120\n")
c.hook(c.write("src/app.py", "x = 1\n"))
expect_contains("the project's line length replaces the default", "--line-length 120 ", c.args())

c = Case("missing-ruff")
(BIN / "ruff").unlink()
c.hook(c.write("src/app.py", "from os import *\n"))
RUFF_NOTICE = "Notice: ruff is not installed, so detectors ruff:F403, ruff:S101 did not run. Their guidelines apply as warnings."
expect_contains("a missing tool is named in the context", RUFF_NOTICE, c.context())
expect_contains("its guideline follows as a warning", "[py.import.no-star] warn (detector unavailable)", c.context())
expect_equal("the user sees the same notice", RUFF_NOTICE, c.message())
expect_equal("a missing tool never denies", "", c.decision())
c.hook(c.write("src/app.py", "from os import *\n"))
expect_contains("the notice repeats on each call the tool is missing", RUFF_NOTICE, c.context())
expect_equal("the user is told only once", None, c.message())
install_stub("ruff", RUFF_STUB)

c = Case("wrong-program")
c.hook(c.write("src/app.py", "x = 1\n"), RUFF_VERSION="Usage: sg group")
expect_contains("another program under the tool's name is not run",
                "Notice: ruff is not the expected program, so detectors", c.context())

c = Case("timeout")
started = time.monotonic()
c.hook(c.write("src/app.py", "x = 1\n"), RUFF_SLEEP="5")
expect_contains("a slow tool is cut off and named", "Notice: ruff timed out after 1.5 s, so detectors", c.context())
expect_equal("the hook returns before the slow tool ends", True, time.monotonic() - started < 5)

c = Case("eslint-missing")
(BIN / "eslint").unlink()
c.hook(c.write("a.ts", "var x = 1\n"))
expect_contains("missing eslint is named", "Notice: eslint is not installed", c.context())
expect_contains("the TypeScript guideline follows as a warning", "[ts.binding.no-var] warn (detector unavailable)", c.context())
expect_equal("missing eslint never denies", "", c.decision())
install_stub("eslint", ESLINT_STUB)

NO_VAR_ROW = '[{"messages":[{"ruleId":"no-var","line":1,"severity":2}]}]'
c = Case("eslint-no-config")
c.hook(c.write("a.ts", "var x = 1\n"), ESLINT_JSON=NO_VAR_ROW)
expect_contains("eslint does not run without a project config",
                "Notice: eslint has no project config, so detectors eslint:no-var did not run.", c.context())
expect_equal("eslint was not started", "", c.args("eslint"))

c = Case("eslint-package-config")
c.file("package.json", '{"eslintConfig": {"rules": {"no-var": "error"}}}\n')
c.hook(c.write("a.ts", "var x = 1\n"), ESLINT_JSON=NO_VAR_ROW)
expect_equal("an eslintConfig in package.json is a project config", "deny", c.decision())
c.file("package.json", '{"name": "demo"}\n')
c.hook(c.write("b.ts", "var x = 1\n"), ESLINT_JSON=NO_VAR_ROW)
expect_contains("a package.json without eslintConfig is not",
                "eslint has no project config", c.context())

c = Case("eslint-shared-config")
c.file("packages/web/eslint.config.mjs", "import rules from '../../tools/rules.mjs';\nexport default [{ rules }];\n")
c.file("tools/rules.mjs", "export default {};\n")
c.file("packages/web/main.ts", "let x = 1\n")
c.file(".eslintignore", "dist/\n")
c.file("packages/cfg/index.mjs", "export default {};\n")
c.file("packages/web/other.mjs", "export default {};\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: tools/rules.mjs\n@@\n-export default {};\n+export default { 'no-var': 'off' };\n"
                             "*** Add File: packages/web/new0.ts\n+var x = 1\n*** End Patch"),
       harness="codex", ESLINT_LOADED=os.pathsep.join(str(c.project / p) for p in ['tools/rules.mjs']), ESLINT_JSON=NO_VAR_ROW)
expect_contains("a module the flat config imports counts as a setting", "also changes tools/rules.mjs", str(c.output()))
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: packages/web/eslint.config.ts\n+export default [];\n"
                             "*** Add File: packages/web/new9.ts\n+var x = 1\n*** End Patch"),
       harness="codex", ESLINT_LOADED="?" + str(c.project / "packages/web/eslint.config.ts"), ESLINT_JSON=NO_VAR_ROW)
expect_equal("an outranked flat config ESLint only looked for is not a setting", "deny", c.decision())
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: .eslintignore\n@@\n-dist/\n+packages/web/main.ts\n"
                             "*** Add File: packages/web/new1.ts\n+var x = 1\n*** End Patch"),
       harness="codex", ESLINT_JSON=NO_VAR_ROW)
expect_contains("an .eslintignore counts as an ignore file, also in flat mode", "also changes .eslintignore", str(c.output()))
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: packages/web/other.mjs\n@@\n-export default {};\n+export default 1;\n"
                             "*** Add File: packages/web/new2.ts\n+var x = 1\n*** End Patch"),
       harness="codex", ESLINT_JSON=NO_VAR_ROW)
expect_equal("a module the config does not load is not a setting", "deny", c.decision())
(c.project / "node_modules" / "@org").mkdir(parents=True)
(c.project / "node_modules" / "@org" / "cfg").symlink_to(c.project / "packages" / "cfg")
c.file("packages/web/eslint.config.mjs", "import shared from '@org/cfg';\nexport default [shared];\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: packages/cfg/index.mjs\n@@\n-export default {};\n+export default { rules: {} };\n"
                             "*** Add File: packages/web/new3.ts\n+var x = 1\n*** End Patch"),
       harness="codex", ESLINT_LOADED=os.pathsep.join(str(c.project / p) for p in ['packages/cfg/index.mjs']), ESLINT_JSON=NO_VAR_ROW)
expect_contains("a workspace package the config imports counts as a setting", "also changes packages/cfg/index.mjs", str(c.output()))
c.file("packages/cfg/index.mjs", "import base from '@org/base';\nexport default base;\n")
c.file("packages/base/package.json", '{"exports": {".": "./main.mjs"}}\n')
c.file("packages/base/main.mjs", "export default {};\n")
(c.project / "node_modules" / "@org" / "base").symlink_to(c.project / "packages" / "base")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: packages/base/main.mjs\n@@\n-export default {};\n+export default { rules: {} };\n"
                             "*** Add File: packages/web/new4.ts\n+var x = 1\n*** End Patch"),
       harness="codex", ESLINT_LOADED=os.pathsep.join(str(c.project / p) for p in ['packages/cfg/index.mjs', 'packages/base/main.mjs']), ESLINT_JSON=NO_VAR_ROW)
expect_contains("a workspace package another one imports counts", "also changes packages/base/main.mjs", str(c.output()))

c = Case("eslint-legacy-settings")
c.file(".eslintrc.json", '{"root": true, "extends": "@acme"}\n')
c.file("packages/acme/package.json", '{"main": "index.cjs"}\n')
c.file("packages/acme/index.cjs", "module.exports = {};\n")
(c.project / "node_modules" / "@acme").mkdir(parents=True)
(c.project / "node_modules" / "@acme" / "eslint-config").symlink_to(c.project / "packages" / "acme")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: packages/acme/index.cjs\n@@\n-module.exports = {};\n+module.exports = { rules: {} };\n"
                             "*** Add File: new0.js\n+var x = 1;\n*** End Patch"),
       harness="codex", ESLINT_LOADED=os.pathsep.join(str(c.project / p) for p in ['packages/acme/index.cjs']), ESLINT_JSON=NO_VAR_ROW)
expect_contains("a scoped legacy extends name resolves to its eslint-config package",
                "also changes packages/acme/index.cjs", str(c.output()))
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: eslint.config.mjs\n+export default [];\n"
                             "*** Add File: new1.js\n+var x = 1;\n*** End Patch"),
       harness="codex", ESLINT_JSON=NO_VAR_ROW, ESLINT_USE_FLAT_CONFIG="false")
expect_equal("with flat mode off, a flat config is not a setting", "deny", c.decision())
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: new3.js\n+var x = 1;\n*** End Patch"),
       harness="codex", ESLINT_JSON=NO_VAR_ROW, ESLINT_USE_FLAT_CONFIG="false", ESLINT_LOADED=str(c.project / "new3.js"))
expect_equal("in legacy mode the code file ESLint reads is not its own setting", "deny", c.decision())
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: src/.eslintignore\n+new2.js\n"
                             "*** Add File: src/new2.js\n+var x = 1;\n*** End Patch"),
       harness="codex", ESLINT_JSON=NO_VAR_ROW)
expect_contains("a nested .eslintignore counts as an ignore file", "also changes src/.eslintignore", str(c.output()))

c = Case("eslint-folder-main")
c.file("eslint.config.cjs", "module.exports = require('./lint');\n")
c.file("lint/package.json", '{"main": "rules.cjs"}\n')
c.file("lint/rules.cjs", "module.exports = [];\n")
c.file("lint/other.cjs", "module.exports = [];\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: lint/rules.cjs\n@@\n-module.exports = [];\n+module.exports = [{}];\n"
                             "*** Add File: new.js\n+var x = 1;\n*** End Patch"),
       harness="codex", ESLINT_LOADED=os.pathsep.join(str(c.project / p) for p in ['lint/rules.cjs']), ESLINT_JSON=NO_VAR_ROW)
expect_contains("a folder's package.json main counts as a loaded file", "also changes lint/rules.cjs", str(c.output()))
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: lint/other.cjs\n@@\n-module.exports = [];\n+module.exports = [{}];\n"
                             "*** Add File: new2.js\n+var x = 1;\n*** End Patch"),
       harness="codex", ESLINT_JSON=NO_VAR_ROW, ESLINT_LOADED="none")
expect_contains("when ESLint's loaded files are unknown, a changed module counts", "also changes lint/other.cjs", str(c.output()))
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: new5.js\n+var x = 1;\n*** End Patch"),
       harness="codex", ESLINT_JSON=NO_VAR_ROW, ESLINT_LOADED="none")
expect_equal("when ESLint's loaded files are unknown, the code file alone still denies", "deny", c.decision())
c.file("eslint.config.js", "export default [];\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: eslint.config.mjs\n+export default [];\n"
                             "*** Add File: new3.js\n+var x = 1;\n*** End Patch"),
       harness="codex", ESLINT_JSON=NO_VAR_ROW)
expect_equal("a flat config that an eslint.config.js outranks is not a setting", "deny", c.decision())
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: local-rules.json\n+{}\n"
                             "*** Add File: new6.js\n+var x = 1;\n*** End Patch"),
       harness="codex", ESLINT_JSON=NO_VAR_ROW, ESLINT_LOADED=str(c.project / "local-rules.json"))
expect_contains("an absent file the config looks for counts when the edit adds it", "also changes local-rules.json", str(c.output()))
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: lint/sub/package.json\n+{}\n"
                             "*** Add File: new7.js\n+var x = 1;\n*** End Patch"),
       harness="codex", ESLINT_JSON=NO_VAR_ROW, ESLINT_LOADED=str(c.project / "lint" / "sub" / "rules.cjs"))
expect_contains("an added package.json above a loaded file counts", "also changes lint/sub/package.json", str(c.output()))
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: notes/package.json\n+{}\n"
                             "*** Add File: new8.js\n+var x = 1;\n*** End Patch"),
       harness="codex", ESLINT_JSON=NO_VAR_ROW)
expect_equal("an added package.json above no loaded file is not a setting", "deny", c.decision())
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: src/allow-var.json\n+{}\n"
                             "*** Add File: new9.js\n+var x = 1;\n*** End Patch"),
       harness="codex", ESLINT_JSON=NO_VAR_ROW)
expect_contains("a changed data file counts without a trace", "also changes src/allow-var.json", str(c.output()))
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: src/.gitignore\n+dist\n"
                             "*** Add File: new10.js\n+var x = 1;\n*** End Patch"),
       harness="codex", ESLINT_JSON=NO_VAR_ROW)
expect_contains("a changed ignore file counts without a trace", "also changes src/.gitignore", str(c.output()))
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: src/policy.tsx\n+export const level = 'off';\n"
                             "*** Add File: new11.js\n+var x = 1;\n*** End Patch"),
       harness="codex", ESLINT_JSON=NO_VAR_ROW, ESLINT_LOADED="none")
expect_contains("with no trace, a changed TSX file counts", "also changes src/policy.tsx", str(c.output()))
expect_contains("with no trace, the notice says the files could not be listed",
                "could not be listed", str(c.output()))
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: eslint-rules/off.mjs\n+export default {};\n"
                             "*** Add File: new12.js\n+var x = 1;\n*** End Patch"),
       harness="codex", ESLINT_JSON=NO_VAR_ROW, ESLINT_LOADED=str(c.project / "eslint-rules" / "*"))
expect_contains("a file added to a folder the config lists counts", "also changes eslint-rules/off.mjs", str(c.output()))
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: eslint-rules/web/off.mjs\n+export default {};\n"
                             "*** Add File: new13.js\n+var x = 1;\n*** End Patch"),
       harness="codex", ESLINT_JSON=NO_VAR_ROW, ESLINT_LOADED=str(c.project / "eslint-rules" / "*"))
expect_contains("a file added below a listed folder counts", "also changes eslint-rules/web/off.mjs", str(c.output()))
expect_lacks("with a trace, the notice does not say it failed", "could not be listed", str(c.output()))


c = Case("ruff-gitignore")
subprocess.run(["git", "init", "-q", str(c.project)], check=True)
if not (BIN / "git").exists():
    (BIN / "git").symlink_to(shutil.which("git"))
c.file(".gitignore", "made/\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: made/out.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW)
expect_equal("a file git ignores is not denied, as Ruff skips it", "", c.decision())
expect_contains("and the notice says so", "git ignores it", str(c.output()))
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: .gitignore\n@@\n-made/\n+kept/\n"
                             "*** Add File: kept/out.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW)
expect_contains("a .gitignore change in the same edit counts as a Ruff setting", "also changes .gitignore", str(c.output()))
c.file(".ignore", "skipme.py\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: skipme.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW)
expect_equal("a file a .ignore may exclude is not denied", "", c.decision())
expect_contains("and the notice says the scope is not known", "could not tell whether a .ignore file or git excludes", str(c.output()))
c.file("base.toml", "respect-gitignore = false\n")
c.file("ruff.toml", 'extend = "base.toml"\nrespect-gitignore = true\n')
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: made/two.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW)
expect_equal("a child config's respect-gitignore beats the one it extends", "", c.decision())
(c.project / "ruff.toml").unlink()
c.file("sub/.ignore", "sub/foo.py\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: sub/foo.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW)
expect_contains("a nested .ignore is unknown, not a skip", "could not tell whether a .ignore", str(c.output()))
(c.project / "sub" / ".ignore").unlink()
(c.project / ".ignore").unlink()
c.file("src/ruff.toml", "respect-gitignore = true\n")
c.file("ruff.toml", "respect-gitignore = false\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: src/made/x.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW)
expect_contains("a root run with another respect-gitignore is unknown", "could not tell whether a .ignore file or git", str(c.output()))
(c.project / "ruff.toml").unlink()
(c.project / "src" / "ruff.toml").unlink()
c.file(".ignore", "!made/neg.py\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: made/neg.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW)
expect_contains("a .ignore that can un-ignore a git-ignored file is unknown, not a skip", "could not tell whether a .ignore", str(c.output()))
(c.project / ".ignore").unlink()
c.file("local-excludes", "localx.py\n")
with (c.project / ".git" / "config").open("a") as config:
    config.write(f"[core]\n\texcludesFile = {c.project / 'local-excludes'}\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: localx.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW)
expect_equal("a repository's own core.excludesFile is not used, as in Ruff", "deny", c.decision())
with (c.project / ".git" / "config").open("a") as config:
    config.write("[core]\n\tignoreCase = true\n")
c.file(".gitignore", "made/\nCASEY.PY\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: casey.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW)
expect_equal("git's core.ignoreCase is not used, as Ruff matches case-sensitively", "deny", c.decision())
c = Case("ruff-ignore-no-git")
c.file(".ignore", "skipme.py\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: skipme.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW)
expect_equal("outside a git repository a .ignore is unknown, so no deny", "", c.decision())
c = Case("eslint-imported-flat-name")
c.file("eslint.config.js", "module.exports = require('./eslint.config.cjs');\n")
c.file("eslint.config.cjs", "module.exports = [];\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: eslint.config.cjs\n@@\n-module.exports = [];\n+module.exports = [{}];\n"
                             "*** Add File: new14.js\n+var x = 1;\n*** End Patch"),
       harness="codex", ESLINT_JSON=NO_VAR_ROW, ESLINT_LOADED="eslint.config.cjs")
expect_contains("an outranked config name the config loads counts", "also changes eslint.config.cjs", str(c.output()))
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: eslint.config.cjs\n@@\n-module.exports = [];\n+module.exports = [{}];\n"
                             "*** Add File: new15.js\n+var x = 1;\n*** End Patch"),
       harness="codex", ESLINT_JSON=NO_VAR_ROW)
expect_equal("an outranked config name ESLint only looked for does not stop a deny", "deny", c.decision())
c.file("real16.js", "const a = 1;\n")
(c.project / "link16.js").symlink_to(c.project / "real16.js")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Delete File: link16.js\n*** Add File: link16.js\n+var a = 1;\n*** End Patch"),
       harness="codex", ESLINT_JSON=NO_VAR_ROW, ESLINT_LOADED="*")
expect_equal("a file that replaces a symlink is not its own setting", "deny", c.decision())
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Delete File: link16.js\n*** Add File: link16.js\n+var a = 1;\n*** End Patch"),
       harness="codex", ESLINT_JSON=NO_VAR_ROW, ESLINT_LOADED="none")
expect_equal("also when the trace is unknown", "deny", c.decision())
c = Case("eslint-config-symlink")
c.file("lint-entry.js", "module.exports = [];\n")
(c.project / "eslint.config.js").symlink_to(c.project / "lint-entry.js")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: lint-entry.js\n@@\n-module.exports = [];\n+var rules = {};\n*** End Patch"),
       harness="codex", ESLINT_JSON=NO_VAR_ROW, ESLINT_ONLY="var ", ESLINT_LOADED="lint-entry.js")
expect_contains("the real file behind a config symlink is a setting of itself", "also changes lint-entry.js", str(c.output()))
NODE = shutil.which("node")
if NODE:
    trace = Case("eslint-recorder")
    trace.file("enabled", "")
    trace.file("rules.cjs", "module.exports = 1;\n")
    trace.file("probe.cjs", "const fs = require('node:fs'); const path = require('node:path');\n"
               "const { promisify } = require('node:util');\n"
               "try { fs.realpathSync(path.join(__dirname, 'overrides.cjs')); } catch {}\n"
               "promisify(fs.exists)(path.join(__dirname, 'enabled')).then((on) => { if (on) require('./rules.cjs'); });\n")
    listed = trace.project / "listed.txt"
    process = subprocess.run([NODE, "probe.cjs"], cwd=trace.project, capture_output=True, text=True, env=os.environ | {
        "NODE_OPTIONS": f"--require {ENGINE.parent / 'eslint_loaded.cjs'}", "PSTACK_ESLINT_LOADED": str(listed)})
    names = listed.read_text() if listed.exists() else ""
    expect_equal("the recorder keeps fs.exists working with promisify", 0, process.returncode)
    expect_contains("so the file loaded after it is listed", str((trace.project / "rules.cjs").resolve()), names)
    expect_contains("a realpath lookup of an absent file is listed", str(trace.project.resolve() / "overrides.cjs"), names)
    trace.file("eslint.config.cjs", "")
    trace.file("lib.js", "")
    trace.file("own.cjs", "require('node:fs').existsSync(require('node:path').join(__dirname, 'eslint.config.cjs')); require('./lib');\n")
    listed.unlink(missing_ok=True)
    subprocess.run([NODE, "own.cjs"], cwd=trace.project, capture_output=True, env=os.environ | {
        "NODE_OPTIONS": f"--require {ENGINE.parent / 'eslint_loaded.cjs'}", "PSTACK_ESLINT_LOADED": str(listed)})
    recorded = listed.read_text().splitlines() if listed.exists() else []
    expect_equal("a look-up the config makes itself counts as a read", True, str((trace.project / "eslint.config.cjs").resolve()) in recorded)
    expect_equal("a lookup candidate Node tries after the found file is left out", False, any(line.endswith("lib.cjs") for line in recorded))
    expect_equal("one it tries before is kept", True, str(trace.project.resolve() / "lib") in recorded)
    trace.file("rules/index.js", "module.exports = 1;\n")
    trace.file("res.cjs", "try { require.resolve('./absent.cjs'); } catch {} require('./rules');\n")
    listed.unlink(missing_ok=True)
    subprocess.run([NODE, "res.cjs"], cwd=trace.project, capture_output=True, env=os.environ | {
        "NODE_OPTIONS": f"--require {ENGINE.parent / 'eslint_loaded.cjs'}", "PSTACK_ESLINT_LOADED": str(listed)})
    recorded = listed.read_text().splitlines() if listed.exists() else []
    expect_equal("a require.resolve the config makes counts as a read", True, str(trace.project.resolve() / "absent.cjs") in recorded)
    expect_equal("an extension require does not try is not a candidate", False, any(line.endswith("rules.cjs") for line in recorded))
    expect_equal("one it does try is", True, str(trace.project.resolve() / "rules.js") in recorded)
    trace.file("pkgdir/index.js", "module.exports = 1;\n")
    trace.file("preset/package.json", '{"main": "src/preset"}\n')
    trace.file("preset/src/preset.json", "{}\n")
    trace.file("dirs.cjs", "require('./pkgdir/'); require('./preset');\n")
    listed.unlink(missing_ok=True)
    subprocess.run([NODE, "dirs.cjs"], cwd=trace.project, capture_output=True, env=os.environ | {
        "NODE_OPTIONS": f"--require {ENGINE.parent / 'eslint_loaded.cjs'}", "PSTACK_ESLINT_LOADED": str(listed)})
    recorded = listed.read_text().splitlines() if listed.exists() else []
    expect_equal("a name ending in / tries no sibling file", False, str(trace.project.resolve() / "pkgdir.js") in recorded)
    expect_equal("a package main tries its extensions in order", True, str(trace.project.resolve() / "preset/src/preset.js") in recorded)
    trace.file("config/linked.js", "module.exports = 1;\n")
    (trace.project / "linked.js").symlink_to(trace.project / "config" / "linked.js")
    trace.file("native.cjs", "require('node:fs').realpathSync.native(require('node:path').join(__dirname, 'eslint.config.cjs')); require('./linked');\n")
    listed.unlink(missing_ok=True)
    subprocess.run([NODE, "native.cjs"], cwd=trace.project, capture_output=True, env=os.environ | {
        "NODE_OPTIONS": f"--require {ENGINE.parent / 'eslint_loaded.cjs'}", "PSTACK_ESLINT_LOADED": str(listed)})
    recorded = listed.read_text().splitlines() if listed.exists() else []
    expect_equal("a realpathSync.native look-up by the config counts as a read", True, str(trace.project.resolve() / "eslint.config.cjs") in recorded)
    expect_equal("candidates stop at a symlink Node resolved", False, any("linked/index" in line for line in recorded))
    trace.file("eslint.config.mjs", "")
    trace.file("node_modules/disc/index.js", "module.exports = () => new Promise((done) => done(require('node:fs').existsSync(require('node:path').join(process.cwd(), 'eslint.config.mjs'))));\n")
    trace.file("node_modules/disc/run.js", "require('./index.js')();\n")
    trace.file("disc.cjs", "require('disc')();\n")
    listed.unlink(missing_ok=True)
    subprocess.run([NODE, "node_modules/disc/run.js"], cwd=trace.project, capture_output=True, env=os.environ | {
        "NODE_OPTIONS": f"--require {ENGINE.parent / 'eslint_loaded.cjs'}", "PSTACK_ESLINT_LOADED": str(listed)})
    recorded = listed.read_text().splitlines() if listed.exists() else []
    expect_equal("a look-up with only node_modules code on the stack is only a look-up", True, "?" + str(trace.project.resolve() / "eslint.config.mjs") in recorded)
    listed.unlink(missing_ok=True)
    subprocess.run([NODE, "disc.cjs"], cwd=trace.project, capture_output=True, env=os.environ | {
        "NODE_OPTIONS": f"--require {ENGINE.parent / 'eslint_loaded.cjs'}", "PSTACK_ESLINT_LOADED": str(listed)})
    recorded = listed.read_text().splitlines() if listed.exists() else []
    expect_equal("a look-up project code makes through a library counts as a read", True, str(trace.project.resolve() / "eslint.config.mjs") in recorded)
c = Case("ruff-symlink-extend")
c.file("ruff.toml", 'extend = "b/config.toml"\n')
c.file("a/source/config.toml", 'extend = "../shared.toml"\n')
(c.project / "b").symlink_to(c.project / "a" / "source")
c.file("shared.toml", '[lint]\nselect = ["F403"]\n')
c.file("a/shared.toml", '[lint]\nignore = ["F403"]\n')
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: shared.toml\n@@\n [lint]\n+ignore = [\"F403\"]\n"
                             "*** Add File: app.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW)
expect_contains("extend follows the path through a symlink, as Ruff does", "also changes shared.toml", str(c.output()))

c = Case("codex-move-chain")
c.file(".ruff.toml", '# original\nlint.select = ["F403"]\n')
c.file("candidate.toml", '# original\nlint.select = ["F403"]\n')
c.file("ruff.toml", 'lint.ignore = ["F403"]\n')
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: candidate.toml\n*** Move to: .ruff.toml\n@@\n-# original\n+# moved\n"
                             "*** Update File: .ruff.toml\n*** Move to: archive.toml\n@@\n-lint.select = [\"F403\"]\n+lint.select = []\n"
                             "*** Add File: app.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW)
expect_contains("a config a move chain leaves empty counts", "also changes .ruff.toml", str(c.output()))

c = Case("eslint-nested-config")
c.file("eslint.config.js", "export default [];\n")
c.file("packages/api/eslint.config.js", "export default [];\n")
c.hook(c.write("packages/api/f.js", "var x = 1;\n"))
expect_equal("eslint runs in the folder of the nearest config, so ESLint 9 loads it",
             str(c.project / "packages" / "api"), (WORK / "eslint.cwd").read_text())

c = Case("bom")
c.hook(c.write("app.py", "\ufeffitems = [[1]]\nx = [a for b in items for a in b]\n"))
expect_equal("a UTF-8 BOM does not stop the comprehension check", "deny", c.decision())

c = Case("ruff-lint-over-top")
c.file("ruff.toml", 'select = ["F"]\n[lint]\nselect = ["E"]\n')
c.hook(c.write("app.py", "x = 1\n"), PSTACK_GUIDELINES_DIR=str(PLUGIN / "skills" / "principle-code-quality" / "guidelines"))
expect_contains("a [lint] select replaces the top-level one", "F403", c.args().splitlines()[-1])

c = Case("eslint-legacy-nested")
c.file(".eslintrc.json", '{"root": true}\n')
c.file("packages/api/.eslintrc.json", "{}\n")
c.hook(c.write("packages/api/f.js", "var x = 1;\n"))
expect_equal("a legacy config runs eslint at the root, where it reads .eslintignore",
             str(c.project), (WORK / "eslint.cwd").read_text())
expect_equal("and in legacy mode", "false", (WORK / "eslint.env").read_text())
c.file("packages/api/eslint.config.js", "export default [];\n")
c.hook(c.write("packages/api/f.js", "var x = 2;\n"), ESLINT_USE_FLAT_CONFIG="false")
expect_equal("with flat mode turned off, a nested flat config is not used",
             str(c.project), (WORK / "eslint.cwd").read_text())
c.hook(c.write("packages/api/f.js", "var x = 3;\n"))
expect_equal("otherwise the nearest flat config folder is used",
             str(c.project / "packages/api"), (WORK / "eslint.cwd").read_text())
expect_equal("in flat mode", "", (WORK / "eslint.env").read_text())

c = Case("eslint-package-install")
c.file("packages/api/eslint.config.js", "export default [];\n")
local = c.file("packages/api/node_modules/.bin/eslint", ESLINT_STUB.replace('"eslint.cwd"', '"eslint.local"'))
local.chmod(0o755)
(WORK / "eslint.local").unlink(missing_ok=True)
c.hook(c.write("packages/api/f.js", "var x = 1;\n"))
expect_equal("eslint installed in the package is used for its files", True, (WORK / "eslint.local").exists())

c = Case("codex-subfolder")
c.file(".git/HEAD", "ref: refs/heads/main\n")
c.file("ruff.toml", '[lint]\nignore = ["F403"]\n')
payload = c.patch("PreToolUse", "*** Begin Patch\n*** Add File: helpers.py\n+from math import *\n*** End Patch")
payload["cwd"] = str(c.project / "src")
c.hook(payload, harness="codex", CLAUDE_PROJECT_DIR="")
expect_lacks("a Codex session below the git root still uses the project's ruff config", "--isolated",
             c.args().splitlines()[-1])

c = Case("eslint-config")
c.file("eslint.config.js", "export default [];\n")
c.hook(c.write("a.ts", "var x = 1\n"), ESLINT_JSON=NO_VAR_ROW)
expect_equal("eslint runs with the project's config and its hit blocks", f"""{BLOCKED}

{announce("ts.binding.no-var")}

[ts.binding.no-var] block: eslint:no-var at a.ts:1
{NO_VAR}""", c.reason())
expect_equal("eslint gets no rule overrides", f"--stdin --stdin-filename {c.project}/a.ts -f json", c.args("eslint"))

c = Case("dedupe")
c.file("pages.py", "x = [f(g(a)) for a in b]\n")
c.hook(c.tool("PostToolUse", "Write", "pages.py"))
expect_contains("the first finding carries the guidance", f"at pages.py:1\n{NESTED_CALL}", c.context())
expect_contains("and is announced", announce("py.comprehension.no-nested-call", "py.data.dataclass-over-dict"), c.context())
for _ in range(19):
    c.hook(c.prompt("hello"))
expect_equal("an unrelated prompt says nothing", "", c.stdout)
c.hook(c.tool("PostToolUse", "Write", "pages.py"))
expect_contains("inside the window the guidance is not repeated",
                "[py.comprehension.no-nested-call] warn: code_quality:CQ002 at pages.py:1 (guidance sent earlier)", c.context())
expect_lacks("and no guideline is announced again", "pstack code quality:", c.context())
c.hook(c.prompt("hello SECRET-PROMPT-WORD"))
c.hook(c.tool("PostToolUse", "Write", "pages.py"))
expect_contains("after 20 prompts the guidance is sent again", f"at pages.py:1\n{NESTED_CALL}", c.context())
expect_contains("and announced again", announce("py.comprehension.no-nested-call"), c.context())
stored = [p for p in (WORK / "data").rglob("*") if p.is_file() and b"SECRET-PROMPT-WORD" in p.read_bytes()]
expect_equal("state never stores prompt text", [], stored)

c = Case("keyword")
c.hook(c.prompt("flatten the lists in parser.py"))
expect_contains("a keyword with a language context fires", f"[py.comprehension.one-for] warn\n{ONE_FOR}", c.context())
expect_contains("the file path in the prompt detects the language", "[py.data.dataclass-over-dict] warn", c.context())
expect_contains("a prompt's guidelines are announced",
                announce("py.comprehension.one-for", "py.data.dataclass-over-dict"), c.context())
c = Case("keyword-alone")
c.hook(c.prompt("flatten the pancake"))
expect_equal("a keyword with no language context says nothing", "0:", f"{c.status}:{c.stdout}")

for name, language in (("x.cs.pp", "csharp"), ("foo.rs.in", "rust"), ("X.PY", "python")):
    c.engine("--language", name)
    expect_equal(f"{name} is {language}", f"{language}\n", c.stdout)

c = Case("invalid")
bad = WORK / "with-bad"
shutil.copytree(FIXTURES, bad)
(bad / "bad.md").write_text("---\nid: bad\nlanguages: python\nscope: global\nenabled: true\ndetectors:\n---\nBody.\n")
c.hook(c.write("pages.py", EXPLICIT_LOOP), PSTACK_GUIDELINES_DIR=str(bad))
expect_contains("an invalid guideline file is skipped and named",
                "Notice: skipped invalid guideline file bad.md: missing key severity", c.context())
expect_contains("the other guidelines still arrive", "[py.data.dataclass-over-dict] warn", c.context())


def failed_json(log=True):
    details = f" Details: {LOG}" if log else ""
    return {"systemMessage": FAILURE_TEXT + details}


FAILURE_TEXT = FAILED_TEXT
c = Case("crash")
NOT_DIR = WORK / "not-a-directory"
NOT_DIR.touch()
c.hook(c.write("pages.py", PAGES), PSTACK_GUIDELINES_DIR=str(NOT_DIR))
expect_equal("an engine failure exits 0", 0, c.status)
expect_json("an engine failure tells the user and does not deny", failed_json(), c.stdout)
expect_contains("the failure is logged", "NotADirectoryError", LOG.read_text())
c.hook("{}", harness="bogus")
expect_json("a wrapper-caught failure names the log it wrote", failed_json(), c.stdout)
expect_contains("and logs the engine's error", "bogus exit 64", LOG.read_text())
(WORK / "data-link").symlink_to(WORK / "data")
c.hook("{}", harness="bogus", CLAUDE_PLUGIN_DATA=str(WORK / "data-link"))
expect_json("a wrapper that refuses a symlinked data directory names no log", failed_json(False), c.stdout)
LOG.unlink()
VICTIM = WORK / "victim"
VICTIM.touch()
LOG.symlink_to(VICTIM)
c.hook(c.write("pages.py", PAGES), PSTACK_GUIDELINES_DIR=str(NOT_DIR))
expect_json("a planted log symlink is refused and the user still hears of the failure", failed_json(False), c.stdout)
expect_equal("and the symlink target is untouched", "", VICTIM.read_text())
c.hook("{}", harness="bogus")
expect_json("a wrapper that refuses a log symlink names no log", failed_json(False), c.stdout)
expect_equal("and the wrapper leaves the symlink target untouched", "", VICTIM.read_text())
LOG.unlink()
os.mkfifo(LOG)
c.run([sys.executable, str(HOOK), "bogus"], "{}", timeout=5)
expect_json("a wrapper does not stall on a log that is a FIFO", failed_json(False), c.stdout)
c.run([sys.executable, str(HOOK), "claude"], json.dumps(c.write("pages.py", PAGES)),
      {"PSTACK_GUIDELINES_DIR": str(NOT_DIR)}, timeout=5)
expect_json("the engine does not stall on a log that is a FIFO", failed_json(False), c.stdout)
LOG.unlink()
UNREADABLE = {"systemMessage": "pstack guideline hook skipped this call: its input is not a UTF-8 JSON object, so code-quality guidelines were not checked."}
c.hook("not json")
expect_json("a malformed payload is named", UNREADABLE, c.stdout)
c.hook("[]")
expect_json("a payload that is not an object is named", UNREADABLE, c.stdout)
c.hook(b'{"hook_event_name": "PreToolUse", "content": "\xff"}')
expect_json("a payload that is not UTF-8 is named", UNREADABLE, c.stdout)
c.hook('{"hook_event_name": "PreToolUse", "tool_name": "Write", "cwd": 7, "tool_input": {"file_path": ["a.py"], "content": 3}}')
expect_equal("a payload with wrong types says nothing", "0:", f"{c.status}:{c.stdout}")

c = Case("no-python")
PYTHON_NOTICE = "Notice: code-quality guideline hooks need Python 3.11 or later; none was found, so no guideline checks run in this session."
CALL_NOTICE = "Notice: code-quality guideline hooks need Python 3.11 or later; none was found, so this call was not checked."
OLD_PYTHON = ("import runpy, sys; sys.version_info = (3, 10); sys.argv = [sys.argv[1], 'claude']; "
              "runpy.run_path(sys.argv[0], run_name='__main__')")
c.run([sys.executable, "-c", OLD_PYTHON, str(HOOK)], json.dumps(c.session_start("startup")), {"PATH": str(EMPTY)})
expect_equal("without Python 3.11 the session start tells the user", PYTHON_NOTICE, c.message())
expect_equal("and tells the agent", PYTHON_NOTICE, c.context())
c.run([sys.executable, "-c", OLD_PYTHON, str(HOOK)], json.dumps(c.write("pages.py", PAGES)), {"PATH": str(EMPTY)})
expect_equal("without Python 3.11 other hooks tell the user each call", [0, CALL_NOTICE], [c.status, c.message()])
(BIN / "python3.11").symlink_to(sys.executable)
c.run([sys.executable, "-c", OLD_PYTHON, str(HOOK)], json.dumps(c.write("pages.py", PAGES)))
expect_equal("an old python3 hands the call to a newer Python on PATH", "deny", c.decision())
(BIN / "python3.11").unlink()
c.run([sys.executable, "-c", OLD_PYTHON, str(HOOK)], "[" * 200000 + "]" * 200000, {"PATH": str(EMPTY)})
expect_equal("a wrapper crash still exits 0 with a notice", "0:" + FAILURE_TEXT, f"{c.status}:{c.message()}")
FRESH = WORK / "fresh-data"
c.hook("{}", harness="bogus", CLAUDE_PLUGIN_DATA=str(FRESH))
expect_equal("a new data folder is private to the user", ["0o700", "0o700"],
             [oct(path.stat().st_mode & 0o777) for path in (FRESH, FRESH / "guideline-state")])


def wired(config, event, key="command"):
    found = []
    for group in json.loads((PLUGIN / "hooks" / config).read_text())["hooks"][event]:
        hooks = [[h[key], h["timeout"]] for h in group["hooks"] if "guidelines" in h.get("command", "")]
        found.append({"matcher": group.get("matcher"), "hooks": hooks})
    return found


PROBE = "import sys; sys.exit(sys.version_info < (3, 6))"
NO_PYTHON_JSON = json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": PYTHON_NOTICE},
                             "systemMessage": PYTHON_NOTICE})


CALL_JSON = json.dumps({"systemMessage": CALL_NOTICE})


def chain(harness, last=CALL_JSON):
    return ('for python in python3 python3.14 python3.13 python3.12 python3.11 python; do '
            f"if \"$python\" -I -c '{PROBE}' </dev/null >/dev/null 2>&1; then "
            f'"$python" -I "${{CLAUDE_PLUGIN_ROOT}}/hooks/guidelines.py" {harness} 2>/dev/null '
            f"|| printf '%s\\n' '{json.dumps({'systemMessage': FAILURE_TEXT})}'; exit 0; fi; done; "
            f"printf '%s\\n' '{last}'")


CLAUDE_START = chain("claude", NO_PYTHON_JSON)
CLAUDE_COMMAND = chain("claude")
for event, matcher, timeout in (
    ("SessionStart", "startup|resume|clear|compact", 5), ("UserPromptSubmit", None, 5),
    ("PreToolUse", "Write|Edit|MultiEdit", 10), ("PostToolUse", "Read|Write|Edit|MultiEdit", 15),
):
    command = CLAUDE_START if event == "SessionStart" else CLAUDE_COMMAND
    expect_equal(f"Claude Code {event} wiring", [{"matcher": matcher, "hooks": [[command, timeout]]}],
                 wired("hooks.json", event))
c = Case("wired")
for group in wired("hooks.json", "PreToolUse"):
    for command, _ in group["hooks"]:
        c.run(command, json.dumps(c.write("pages.py", PAGES)))
expect_equal("the wired Claude Code command denies the flattening comprehension", "deny", c.decision())
c.run(CLAUDE_START, json.dumps(c.session_start("startup")), {"PATH": str(EMPTY)})
expect_equal("with no Python on PATH the wired session start tells the user", PYTHON_NOTICE, c.message())
expect_equal("and tells the agent", PYTHON_NOTICE, c.context())
c.run(CLAUDE_COMMAND, json.dumps(c.write("pages.py", PAGES)), {"PATH": str(EMPTY)})
expect_equal("with no Python on PATH other wired hooks exit 0 and tell the user", [0, CALL_NOTICE],
             [c.status, c.message()])
ONLY_PYTHON = WORK / "only-python"
ONLY_PYTHON.mkdir()
(ONLY_PYTHON / "python").symlink_to(sys.executable)
c.run(CLAUDE_COMMAND, json.dumps(c.write("pages.py", PAGES)), {"PATH": str(ONLY_PYTHON)})
expect_equal("the wired command falls back to python when python3 is missing", "deny", c.decision())
SHADOW = WORK / "shadow"
SHADOW.mkdir()
(SHADOW / "json.py").write_text('raise ImportError("shadowed")\n')
c.run(CLAUDE_COMMAND, json.dumps(c.write("pages.py", PAGES)), {"PYTHONPATH": str(SHADOW)})
expect_equal("the wired command ignores PYTHONPATH", "deny", c.decision())
ONLY_312 = WORK / "only-python312"
ONLY_312.mkdir()
(ONLY_312 / "python3.12").symlink_to(sys.executable)
c.run(CLAUDE_COMMAND, json.dumps(c.write("pages.py", PAGES)), {"PATH": str(ONLY_312)})
expect_equal("the wired command finds a versioned python3.12", "deny", c.decision())
BROKEN = WORK / "broken-python3"
BROKEN.mkdir()
(BROKEN / "python3").write_text("#!/no/such/interpreter\n")
(BROKEN / "python3").chmod(0o755)
(BROKEN / "python3.12").symlink_to(sys.executable)
c.run(CLAUDE_COMMAND, json.dumps(c.write("pages.py", PAGES)), {"PATH": f"{BROKEN}:/usr/bin:/bin"})
expect_equal("a python3 that cannot start falls through to the next Python", "deny", c.decision())
(BROKEN / "python3").write_text("#!/bin/sh\ncat >/dev/null\nexit 2\n")
c.run(CLAUDE_COMMAND, json.dumps(c.write("pages.py", PAGES)), {"PATH": f"{BROKEN}:/usr/bin:/bin"})
expect_equal("a python3 that fails the start check is skipped, and the payload reaches the next Python",
             "deny", c.decision())
(BROKEN / "python3").write_text("#!/bin/sh\nIFS= read -r data\nexit 17\n")
c.run(CLAUDE_COMMAND, json.dumps(c.write("pages.py", PAGES)), {"PATH": f"{BROKEN}:/usr/bin:/bin"})
expect_equal("a python3 that reads stdin and fails does not take the payload from the next Python",
             "deny", c.decision())
BROKEN_PLUGIN = WORK / "broken-plugin"
(BROKEN_PLUGIN / "hooks").mkdir(parents=True)
(BROKEN_PLUGIN / "hooks" / "guidelines.py").write_text("import no_such_module_for_the_hook\n")
for command, payload in ((CLAUDE_START, c.session_start("startup")), (CLAUDE_COMMAND, c.write("pages.py", PAGES))):
    c.run(command, json.dumps(payload), {"CLAUDE_PLUGIN_ROOT": str(BROKEN_PLUGIN)})
    expect_equal(f"a wrapper that cannot start says the hook failed ({payload['hook_event_name']})",
                 [0, FAILURE_TEXT], [c.status, c.message()])
ENGINE_DATA = WORK / "engine-data"
c.run(CLAUDE_START, json.dumps(c.session_start("startup")), {"CLAUDE_PLUGIN_DATA": str(ENGINE_DATA)})
expect_equal("the engine's new data folders are private to the user", ["0o700", "0o700"],
             [oct(path.stat().st_mode & 0o777) for path in (ENGINE_DATA, ENGINE_DATA / "guideline-state")])

CODEX_COMMAND = chain("codex")
CODEX_START = chain("codex", NO_PYTHON_JSON)
CODEX_WINDOWS = '"${CLAUDE_PLUGIN_ROOT}/hooks/guidelines.cmd" codex'
for event, matcher, timeout in (
    ("PreToolUse", "apply_patch", 10), ("PostToolUse", "apply_patch", 15), ("UserPromptSubmit", None, 5),
):
    expect_equal(f"Codex {event} wiring", [{"matcher": matcher, "hooks": [[CODEX_COMMAND, timeout]]}],
                 wired("codex-hooks.json", event))
    expect_equal(f"Codex {event} Windows wiring", [{"matcher": matcher, "hooks": [[CODEX_WINDOWS, timeout]]}],
                 wired("codex-hooks.json", event, "commandWindows"))
expect_equal("Codex SessionStart wiring", [{"matcher": "startup|resume|clear|compact", "hooks": [[CODEX_START, 5]]}],
             wired("codex-hooks.json", "SessionStart"))
expect_equal("Codex SessionStart Windows wiring",
             [{"matcher": "startup|resume|clear|compact", "hooks": [[CODEX_WINDOWS + " start", 5]]}],
             wired("codex-hooks.json", "SessionStart", "commandWindows"))
for group in wired("codex-hooks.json", "PreToolUse"):
    for command, _ in group["hooks"]:
        c.run(command, json.dumps(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: wired.py\n" + "".join(
            f"+{row}\n" for row in PAGES.splitlines()) + "*** End Patch")))
expect_equal("the wired Codex command denies the flattening comprehension", "deny", c.decision())

MANY = WORK / "many-guidelines"
MANY.mkdir()
for number in range(60):
    guideline(f"py-many-rule-{number:02d}-with-a-long-name.md", f"Rule {number} body text that is long enough. " * 3,
              f"id: py.many.rule-{number:02d}-with-a-long-name", "languages: python", "scope: global",
              "severity: warn", "enabled: true", "detectors:", folder=MANY)
c = Case("many")
c.hook(c.write("plain.py", "x = 1\n"), PSTACK_GUIDELINES_DIR=str(MANY))
issued = re.findall(r"^\[([^\]]+)\]", c.context(), re.MULTILINE)
named = re.search(r"pstack code quality: (.*) guidelines provided$", c.context(), re.MULTILINE).group(1).split(", ")
expect_equal("the announcement names every guideline the call issued", issued, named)
expect_equal("and the call issued some but not all of them", True, 0 < len(issued) < 60)
expect_equal("and stays inside the size cap", True, len(c.context()) <= 9000)
NOISY = WORK / "noisy-guidelines"
shutil.copytree(FIXTURES, NOISY)
for number in range(45):
    (NOISY / f"invalid-guideline-file-with-a-rather-long-name-{number:02d}.md").write_text("---\nid: bad\n---\nBody.\n")
c = Case("noisy")
c.hook(c.write("pages.py", EXPLICIT_LOOP), PSTACK_GUIDELINES_DIR=str(NOISY))
out = json.loads(c.stdout)
expect_equal("the user's notice and the context stay inside the size cap together", True,
             len(out["systemMessage"]) + len(out["hookSpecificOutput"]["additionalContext"]) <= 9000)
expect_contains("and the notice counts what it left out", "more notices; the agent has them.", out["systemMessage"])
c = Case("noisy-codex")
c.hook(c.session_start("startup"), harness="codex", PSTACK_GUIDELINES_DIR=str(NOISY))
out = json.loads(c.stdout)
expect_contains("Codex also shows notices to the user", "Notice: skipped invalid guideline file", out.get("systemMessage", ""))
expect_equal("and stays inside the size cap with them", True,
             len(out["systemMessage"]) + len(out["hookSpecificOutput"]["additionalContext"]) <= 9000)

ADD_PAGES = "*** Begin Patch\n*** Add File: pages.py\n" + "".join(f"+{row}\n" for row in PAGES.splitlines()) + "*** End Patch"
c = Case("codex-add")
c.hook(c.patch("PreToolUse", ADD_PAGES), harness="codex")
expect_equal("a Codex patch that adds the violation is denied", PAGES_REASON, c.reason())
c.file("pages.py", PAGES.encode() + b"\xff\n")
c.hook(c.patch("PreToolUse", ADD_PAGES), harness="codex")
expect_equal("a Codex Add File over a file that is not UTF-8 does not deny", "", c.decision())
expect_contains("and its findings are warnings",
                "Notice: could not read the current pages.py: it is not UTF-8 text, so its findings are warnings.",
                c.context())

UPDATE = """*** Begin Patch
*** Update File: pages.py
@@ def pages(paths):
     print(len(found))
-    return tuple(found)
+    return tuple(p for q in found for p in q)
*** End Patch"""
c = Case("codex-update")
c.file("pages.py", EXPLICIT_LOOP)
c.hook(c.patch("PreToolUse", UPDATE), harness="codex")
expect_contains("a Codex update hunk is applied in memory and denied",
                "[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:7", c.reason())
expect_contains("and the Codex deny announces the guideline", announce("py.comprehension.one-for"), c.reason())
c.file("pages.py", PAGES)
c.hook(c.patch("PostToolUse", UPDATE), harness="codex")
expect_contains("after a Codex patch the file's findings arrive as warnings",
                "[py.comprehension.one-for] warn: code_quality:CQ001 at pages.py:2", c.context())

c = Case("codex-no-apply")
c.file("pages.py", "x = 1\n")
c.hook(c.patch("PreToolUse", UPDATE), harness="codex")
expect_contains("a Codex patch that does not apply is named",
                "Notice: did not check pages.py: could not build the text this edit leaves, so PostToolUse checks it",
                c.context())
expect_equal("and is not denied", "", c.decision())

c = Case("codex-whitespace")
c.file("pages.py", "def pages(paths):  \r\n    return tuple(found)\r\n")
c.hook(c.patch("PreToolUse", """*** Begin Patch
*** Update File: pages.py
@@
 def pages(paths):
-    return tuple(found)
+    return tuple(p for q in found for p in q)
*** End Patch"""), harness="codex")
expect_contains("a Codex hunk matches past trailing whitespace and CRLF",
                "[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:2", c.reason())

ANCHORED = """*** Begin Patch
*** Update File: demo.py
@@ def target():
-    x = 0
+    x = [a for b in c for a in b]
*** End Patch"""
c = Case("codex-anchor")
c.file("demo.py", 'def first():\n    x = 0\n\ndef target():\n    return """\n    x = 0\n    """\n')
c.hook(c.patch("PreToolUse", ANCHORED), harness="codex")
expect_equal("a Codex hunk goes after its @@ anchor, as Codex puts it", "", c.decision())
c.hook(c.patch("PreToolUse", ANCHORED.replace("def target", "def missing")), harness="codex")
expect_contains("a Codex anchor that is not in the file is named, not denied",
                "Notice: did not check demo.py: could not build the text this edit leaves", c.context())
c.file("demo.py", "x = 0\nx = 0\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: demo.py\n@@\n-x = 0\n+x = [a for b in c for a in b]\n"
                             "*** End of File\n*** End Patch"), harness="codex")
expect_contains("an End of File hunk changes the last match", "code_quality:CQ001 at demo.py:2", c.reason())

c.file("demo.py", '"""\n"""')
c.hook(c.patch("PreToolUse", '*** Begin Patch\n*** Update File: demo.py\n@@\n-"""\n+from os import *\n+"""\n'
                             "*** End of File\n*** End Patch"), harness="codex")
expect_equal("an End of File hunk on a file with no final newline changes its last line, as Codex does",
             '"""\nfrom os import *\n"""\n', (WORK / "ruff.stdin").read_text())
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: demo.py\n@@\n+from os import *\n*** End Patch"),
       harness="codex")
expect_equal("an insertion-only hunk goes after the last line of a file with no final newline",
             '"""\n"""\nfrom os import *\n', (WORK / "ruff.stdin").read_text())
c.file("demo.py", "x = 1\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: demo.py\n@@\n+try:\n+    pass\n@@\n+except:\n+    pass\n"
                             "*** End Patch"), harness="codex")
expect_equal("insertion-only hunks keep patch order, as Codex does",
             "x = 1\ntry:\n    pass\nexcept:\n    pass\n", (WORK / "ruff.stdin").read_text())
c.file("demo.py", "a\nb\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: demo.py\n@@\n+c\n@@\n b\n+d\n*** End Patch"),
       harness="codex")
expect_equal("a hunk is split at its context lines, so insertions at one offset keep Codex's order",
             "a\nb\nc\nd\n", (WORK / "ruff.stdin").read_text())
c.file("demo.py", "import os\n\x0c\ndef f():\n    return 1\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: demo.py\n@@\n import os\n \x0c\n+from math import *\n"
                             " def f():\n*** End Patch"), harness="codex")
expect_equal("a patch splits on newlines only, so a form feed line is context, as in Codex",
             "import os\n\x0c\nfrom math import *\ndef f():\n    return 1\n", (WORK / "ruff.stdin").read_text())
c.file("demo.py", b'def f():\r\n    pass\r\ns = """\n    pass\n"""\n')
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: demo.py\n@@\n-    pass\n+    x = 1\n*** End Patch"),
       harness="codex")
expect_equal("a CRLF line matches before a later LF line, as in Codex",
             'def f():\r\n    x = 1\r\ns = """\n    pass\n"""\n', (WORK / "ruff.stdin").read_bytes().decode())
c.hook(c.patch("PreToolUse", "*** Begin Patch\n  *** Add File: added.py\n+x = [a for b in c for a in b]\n*** End Patch"),
       harness="codex")
expect_equal("a file header with leading spaces is read, as Codex trims it", "deny", c.decision())
c.file("moved.py", "from os import *\nnum = 0\n")
(WORK / "ruff.args").unlink(missing_ok=True)
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: moved.py\n*** Move to: target.py\n@@\n-num = 0\n"
                             "+num = 1\n*** End Patch"), harness="codex", RUFF_JSON=F403_ROW)
expect_contains("a moved file's old findings are scanned at its old path",
                f"--stdin-filename {c.project}/moved.py", c.args())
def codex_result(name: str, before: str | bytes, patch: str, expected: str) -> None:
    c.file("demo.py", before)
    c.hook(c.patch("PreToolUse", f"*** Begin Patch\n{patch}\n*** End Patch"), harness="codex")
    expect_equal(name, expected, (WORK / "ruff.stdin").read_bytes().decode())


codex_result("a second section for one file starts from the first one's text", "from math import *\npass\n",
             "*** Update File: demo.py\n@@\n-from math import *\n+x = 0\n*** Update File: demo.py\n@@\n-pass\n"
             "+from os import *", "x = 0\nfrom os import *\n")
codex_result("an indented move line in an update is context", 'doc = """\n*** Move to: fixture.txt\n"""\npass\n',
             '*** Update File: demo.py\n@@\n doc = """\n *** Move to: fixture.txt\n """\n-pass\n+x = 1',
             'doc = """\n*** Move to: fixture.txt\n"""\nx = 1\n')
codex_result("an anchor's trailing spaces are dropped, as in Codex", '# marker\npass\ndoc = """\n# marker   \npass\n"""\n',
             "*** Update File: demo.py\n@@ # marker   \n-pass\n+x = 1", '# marker\nx = 1\ndoc = """\n# marker   \npass\n"""\n')
codex_result("an End of File line with trailing spaces still ends the hunk", 'doc = """\npass\n"""\npass\n',
             "*** Update File: demo.py\n@@\n-pass\n+x = 1\n*** End of File   ", 'doc = """\npass\n"""\nx = 1\n')
codex_result("a bare CR ends a source line, as in Codex", b'doc = """\r\npass\r"""\rpass\r',
             "*** Update File: demo.py\n@@\n-pass\n+x = 1\n*** End of File", 'doc = """\r\npass\r"""\rx = 1\r\n')
codex_result("new lines take the file's first line ending, as in Codex", b"a\rb\r",
             "*** Update File: demo.py\n@@\n a\n+\n+x", "a\r\rx\rb\r")
c.file("ruff.toml", "[lint]\n")
c.file("demo.py", "x\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: ruff.toml\n@@\n [lint]\n+ignore = [\"F403\"]\n"
                             "*** Add File: newmod.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW)
expect_lacks("an edit that also changes a lint config does not deny", "deny", str(c.output()))
expect_contains("and says why", "also changes ruff.toml", str(c.output()))
c.file("package.json", "{}\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: package.json\n@@\n-{}\n+{\"name\": \"x\"}\n"
                             "*** Add File: newmod2.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW)
expect_equal("a setting file for another tool does not lower the deny", "deny", c.decision())
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Delete File: ruff.toml\n"
                             "*** Add File: newmod3.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW)
expect_contains("deleting a config in the same edit warns", "also changes ruff.toml", str(c.output()))
c.file("cfg/base.toml", "[lint]\n")
c.file("ruff.toml", 'extend = "cfg/base.toml"\n')
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: cfg/base.toml\n@@\n [lint]\n+ignore = [\"F403\"]\n"
                             "*** Add File: newmod4.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW)
expect_contains("changing a config the project config extends warns", "also changes cfg/base.toml", str(c.output()))
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: ruff.toml\n@@\n-extend = \"cfg/base.toml\"\n+extend = \"cfg/other.toml\"\n"
                             "*** Add File: newmod5.py\n+items = [[1]]\n+x = [a for b in items for a in b]\n*** End Patch"),
       harness="codex")
expect_equal("a Ruff config edit does not lower another detector's deny", "deny", c.decision())
c.file("pyproject.toml", "[project]\nname = 'old'\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: pyproject.toml\n@@\n-name = 'old'\n+name = 'new'\n"
                             "*** Add File: newmod6.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW)
expect_equal("a pyproject.toml that Ruff does not read does not lower the deny", "deny", c.decision())
c.file("gone.py", "pass\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: gone.py\n@@\n-pass\n+from math import *\n"
                             "*** Delete File: gone.py\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW)
expect_equal("a file the patch deletes at the end is not denied", "", c.decision())
c.file("shared/base.toml", "[lint]\n")
c.file("ruff.toml", 'extend = "${DOTAI_SHARED}/base.toml"\n')
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: shared/base.toml\n@@\n [lint]\n+ignore = [\"F403\"]\n"
                             "*** Add File: newmod7.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW, DOTAI_SHARED=str(c.project / "shared"))
expect_contains("an extend path with an environment variable is followed", "also changes shared/base.toml", str(c.output()))
shared_env = {"DOTAI_SHARED": str(c.project / "shared")}
many = "".join(f"*** Add File: notes/n{i}.md\n+note\n" for i in range(49))
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: newmod8.py\n+from math import *\n" + many +
                             "*** Update File: shared/base.toml\n@@\n [lint]\n+ignore = [\"F403\"]\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW, **shared_env)
expect_contains("a setting past the file limit still counts", "also changes shared/base.toml", str(c.output()))
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Add File: src/pyproject.toml\n+[project]\n+name = \"demo\"\n"
                             "*** Add File: src/newmod9.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW, **shared_env)
expect_equal("a new pyproject.toml without Ruff settings does not lower the deny", "deny", c.decision())
c.file("gone2.py", "pass\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: gone2.py\n@@\n-pass\n+from math import *\n"
                             "*** Delete File: ./gone2.py\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW, **shared_env)
expect_equal("a delete spelled ./gone2.py cancels the update of gone2.py", "", c.decision())
c.file("alias.py", "pass\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: alias.py\n@@\n-pass\n+from math import *\n"
                             f"*** Update File: {c.project}/alias.py\n@@\n-from math import *\n+import math\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW, **shared_env)
expect_lacks("an absolute and a relative header are one file", "could not build", str(c.output()))
(c.project / "alias-link.py").symlink_to(c.project / "alias.py")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: alias.py\n@@\n-pass\n+from math import *\n"
                             "*** Update File: alias-link.py\n@@\n-from math import *\n+import math\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW, **shared_env)
expect_lacks("a symlink and its target are one file", "could not build", str(c.output()))
rows = ["["] + [f"{i}," for i in range(50000)] + ["null", "]"]
c.file("lookup.json", "\n".join(rows) + "\n")
removed = "\n".join("-" + row for row in rows[38001:50001])
began = time.monotonic()
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: lookup.json\n@@\n" + removed +
                             "\n+0,\n*** Add File: big-hunk.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW, **shared_env)
expect_equal("a 12000-line unanchored hunk still gets checked", "deny", c.decision())
expect_equal("a 12000-line unanchored hunk takes under 3 s", True, time.monotonic() - began < 3)
c.file("schema.json", "[\n" + ("0,\n" + "2,\n" * 71) * 3500 + "3\n]\n")
began = time.monotonic()
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: schema.json\n" + "@@\n-0,\n+1,\n" * 3500 +
                             "*** Add File: many-hunks.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW, **shared_env)
expect_equal("3500 small hunks still get checked", "deny", c.decision())
expect_equal("3500 small hunks take under 3 s", True, time.monotonic() - began < 3)
c.file("data.py", "values = [\n" + "    0,\n" * 130000 + "    2,\n]\n")
began = time.monotonic()
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: data.py\n@@\n" + "-    0,\n" * 15000 +
                             "     2,\n ]\n+from os import *\n*** Add File: repeated.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW, **shared_env)
expect_equal("a hunk of one repeated line still gets checked", "deny", c.decision())
expect_equal("a hunk of one repeated line takes under 3 s", True, time.monotonic() - began < 3)
c.file("target2.py", "pass\n")
(c.project / "link2.py").symlink_to(c.project / "target2.py")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: link2.py\n*** Move to: moved2.py\n@@\n-pass\n+import sys\n"
                             "*** Update File: target2.py\n@@\n-pass\n+from os import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW, **shared_env)
expect_lacks("moving a symlink leaves its target to check", "could not build", str(c.output()))
c.file("real3.py", "pass\n")
(c.project / "link3.py").symlink_to(c.project / "real3.py")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: real3.py\n@@\n-pass\n+x = [a for b in c for a in b]\n"
                             "*** Update File: link3.py\n*** Move to: moved3.py\n@@\n-x = [a for b in c for a in b]\n+x = 1\n*** End Patch"),
       harness="codex", **shared_env)
expect_equal("a symlink moved after its target changed keeps the target's change", "deny", c.decision())
expect_contains("and the deny names the target", "real3.py", str(c.output()))
c.file("real4.py", "pass\n")
(c.project / "link4.py").symlink_to(c.project / "real4.py")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Delete File: link4.py\n*** Add File: link4.py\n+x = [a for b in c for a in b]\n"
                             "*** Update File: link4.py\n*** Move to: moved4.py\n@@\n-x = [a for b in c for a in b]\n+x = 1\n*** End Patch"),
       harness="codex", **shared_env)
expect_lacks("a file added where a symlink was, then moved, is not checked at the old target", "real4.py", str(c.output()))
c.file("deep/real7.py", "pass\n")
(c.project / "link7.py").symlink_to(c.project / "deep" / "real7.py")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Delete File: link7.py\n*** Add File: link7.py\n+x = [a for b in c for a in b]\n*** End Patch"),
       harness="codex", **shared_env)
expect_equal("a file that replaces a deleted symlink is checked", "deny", c.decision())
expect_lacks("at its own path, not the old target", "real7.py", str(c.output()))
c.file("real8.py", "pass\n")
(c.project / "link8.py").symlink_to(c.project / "real8.py")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: link8.py\n*** Move to: real8.py\n@@\n-pass\n+x = [a for b in c for a in b]\n"
                             "*** Add File: link8.py\n+pass\n*** End Patch"),
       harness="codex", **shared_env)
expect_equal("moving a symlink onto its own target keeps the target's change", "deny", c.decision())
expect_contains("and the deny names the target", "real8.py", str(c.output()))
c.file("src10.py", "pass\n")
c.file("build/keep", "")
(c.project / "build" / "alias10.py").symlink_to(c.project / "src10.py")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: src10.py\n@@\n-pass\n+x = [a for b in c for a in b]\n"
                             "*** Update File: build/alias10.py\n@@\n x = [a for b in c for a in b]\n+# note\n*** End Patch"),
       harness="codex", **shared_env)
expect_equal("a later section through a symlink still checks the target at its own path", "deny", c.decision())
expect_contains("and the deny names the target", "src10.py", str(c.output()))
c.file("src11.py", "pass\n")
(c.project / "alias11.py").symlink_to(c.project / "src11.py")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: src11.py\n*** Move to: alias11.py\n@@\n-pass\n+x = [a for b in c for a in b]\n*** End Patch"),
       harness="codex", **shared_env)
expect_equal("a move onto a symlink to the file itself loses the text, so no deny", "", c.decision())
c.file("real12.py", "pass\n")
(c.project / "build" / "alias12.py").symlink_to(c.project / "real12.py")
c.hook(c.write("build/alias12.py", "x = [a for b in c for a in b]\n"), **shared_env)
expect_equal("a Write through a symlink is checked at the target's own path", "deny", c.decision())
c.file("build/real13.py", "pass\n")
(c.project / "link13.py").symlink_to(c.project / "build" / "real13.py")
(c.project / "build" / "link13b.py").symlink_to(c.project / "build" / "real13.py")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: link13.py\n@@\n-pass\n+x = [a for b in c for a in b]\n"
                             "*** Update File: build/link13b.py\n@@\n x = [a for b in c for a in b]\n+# note\n*** End Patch"),
       harness="codex", **shared_env)
expect_equal("each symlink a file was edited through is checked", "deny", c.decision())
expect_contains("and the deny names the first link", "link13.py", str(c.output()))
c.file("a14.py", "pass\n")
(c.project / "build" / "alias14.py").symlink_to(c.project / "a14.py")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: a14.py\n*** Move to: build/alias14.py\n@@\n-pass\n+# moved\n"
                             "*** Add File: build/alias14.py\n+x = [a for b in c for a in b]\n*** End Patch"),
       harness="codex", **shared_env)
expect_equal("an add through the symlink a move left is checked at the real path", "deny", c.decision())
expect_contains("and the deny names it", "a14.py", str(c.output()))
c.file("src/new15.py", "pass\n")
c.file("build/old15.py", "x = [a for b in c for a in b]\n")
(c.project / "build" / "alias15.py").symlink_to(c.project / "src" / "new15.py")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: build/old15.py\n*** Move to: build/alias15.py\n@@\n x = [a for b in c for a in b]\n+# moved\n*** End Patch"),
       harness="codex", **shared_env)
expect_equal("a move onto a symlink keeps the move source's baseline at the real path", "deny", c.decision())
expect_contains("and the deny names the real path", "new15.py", str(c.output()))
c.file("build/real16/app.py", "pass\n")
(c.project / "alias16").symlink_to(c.project / "build" / "real16")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: alias16/app.py\n@@\n-pass\n+x = [a for b in c for a in b]\n*** End Patch"),
       harness="codex", **shared_env)
expect_equal("an edit through a symlinked folder is checked at its own name", "deny", c.decision())
c.file("build/real17.py", "x = [a for b in c for a in b]\n")
(c.project / "middle17.py").symlink_to(c.project / "build" / "real17.py")
(c.project / "build" / "alias17.py").symlink_to(c.project / "middle17.py")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Delete File: middle17.py\n*** Add File: build/alias17.py\n+x = [a for b in c for a in b]\n*** End Patch"),
       harness="codex", **shared_env)
expect_equal("a symlink chain resolves through the links the patch deleted", "deny", c.decision())
expect_contains("and the deny names the new file", "middle17.py", str(c.output()))
c.file("real9.py", "pass\n")
c.file("aliases/keep", "")
(c.project / "aliases" / "alias9.py").symlink_to("../real9.py")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: aliases/alias9.py\n@@\n-pass\n+x = [a for b in c for a in b]\n"
                             "*** Update File: aliases/alias9.py\n*** Move to: aliases/copied9.py\n@@\n x = [a for b in c for a in b]\n*** End Patch"),
       harness="codex", **shared_env)
expect_contains("a symlink updated, then moved, leaves the target checked at its own path", "real9.py", str(c.output()))
c.file("real10.py", "x = [a for b in c for a in b]\n")
(c.project / "aliases" / "alias10.py").symlink_to("../real10.py")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: aliases/alias10.py\n*** Move to: real10.py\n@@\n x = [a for b in c for a in b]\n*** End Patch"),
       harness="codex", **shared_env)
expect_equal("moving a symlink onto its target compares with the target's own text", "", c.decision())
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: ruff.toml\n*** Move to: scratch/old.toml\n@@\n-extend = \"${DOTAI_SHARED}/base.toml\"\n+x = 1\n"
                             "*** Delete File: scratch/old.toml\n*** Add File: newmod10.py\n+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW, **shared_env)
expect_contains("moving a config away and deleting it counts", "also changes ruff.toml", str(c.output()))
(c.project / "ruff.toml").unlink()
c.file("demo.py", "pass\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: demo.py\n*** Move to: moved_out.py\n@@\n-pass\n"
                             "+from math import *\n*** End Patch"),
       harness="codex", RUFF_JSON=F403_ROW, RUFF_STDERR="warning: Ignored path via `extend-exclude`")
expect_lacks("a path ruff excludes counts as checked, with no findings", "could not check the current", str(c.output()))
c.file("demo.py", "if True:\n    a = 1\n    b = 2\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: demo.py\n@@\n a = 1\n-    b = 2\n+    from math import *\n"
                             "*** End Patch"), harness="codex")
expect_equal("a context line matched past whitespace keeps the file's text, as Codex does",
             "if True:\n    a = 1\n    from math import *\n", (WORK / "ruff.stdin").read_text())
c.file("demo.py", "x = 1\r\ny = 2\nz = 3\r\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: demo.py\n@@\n-y = 2\n+from math import *\n"
                             "*** End Patch"), harness="codex")
expect_equal("a file with mixed line endings is patched, as Codex does",
             "x = 1\r\nfrom math import *\r\nz = 3\r\n", (WORK / "ruff.stdin").read_bytes().decode())
c.file("demo.py", "x = 1\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: demo.py\n@@\n+from os import *\n@@\n-x = 1\n+x = 2\n"
                             "*** End of File\n*** End Patch"), harness="codex")
expect_equal("an insertion before an End of File hunk goes after the original last line, as Codex does",
             "x = 2\nfrom os import *\n", (WORK / "ruff.stdin").read_text())
c.file("demo.py", "# release \u2014 notes\npass\n")
c.hook(c.patch("PreToolUse", "*** Begin Patch\n*** Update File: demo.py\n@@ # release - notes\n-pass\n"
                             "+from os import *\n*** End Patch"), harness="codex")
expect_equal("an anchor matches with Unicode dashes read as ASCII, as Codex does",
             "# release \u2014 notes\nfrom os import *\n", (WORK / "ruff.stdin").read_text())

c = Case("comment-only")
c.file("pages.py", PAGES)
c.hook(c.write("pages.py", PAGES.replace("(path)))", "(path)))  # one page per path")))
expect_equal("a comment added to a line that already broke a rule does not deny", "", c.decision())
c.file("app.ts", "var x = 1\n")
c.file("eslint.config.js", "export default [];\n")
c.hook(c.write("app.ts", "var x = 1 // counter\n"), ESLINT_JSON=NO_VAR_ROW)
expect_equal("in TypeScript too", "", c.decision())
c.file("app.js", "/* intro\n * original */ var item = 1;\n")
c.hook(c.write("app.js", "/* intro\n * revised */ var item = 1;\n"),
       ESLINT_JSON='[{"messages":[{"ruleId":"no-var","line":2,"severity":2}]}]')
expect_equal("and when the comment opened on an earlier line", "", c.decision())
c.file("app.js", "var x = 1; // matches */foo\n")
c.hook(c.write("app.js", "var x = 1; // matches foo\n"), ESLINT_JSON=NO_VAR_ROW)
expect_equal("and when a // comment holds */", "", c.decision())
c.file("app.js", "/*\n * old // text */ var x = 1;\n")
c.hook(c.write("app.js", "/*\n * new // text */ var x = 1;\n"),
       ESLINT_JSON='[{"messages":[{"ruleId":"no-var","line":2,"severity":2}]}]')
expect_equal("and when an open block comment holds //", "", c.decision())
c.file("app.js", "var x = /* explanation */ 1;\n")
c.hook(c.write("app.js", "var x = 1;\n"), ESLINT_JSON=NO_VAR_ROW)
expect_equal("and when the comment sits inside the statement", "", c.decision())
c.file("app.js", "var a = 1; var b = 2;\n")
c.hook(c.write("app.js", "var a = 1; let b = 2; var c = 3;\n"),
       ESLINT_JSON='[{"messages":[{"ruleId":"no-var","line":1,"severity":2},'
                   '{"ruleId":"no-var","line":1,"severity":2}]}]')
expect_equal("an edit that keeps a rule's count on a changed line is not denied", "", c.decision())
c.file("flat.py", "x = [a for b in c for a in b]; n = 1\n")
c.hook(c.write("flat.py", "x = [a for b in c for a in b]; n = 2\n"))
expect_equal("a changed line that keeps its old finding is not denied", "", c.decision())
c.hook(c.write("flat.py", "x = [a for b in c for a in b]; n = 2\ny = [a for b in c for a in b]\n"))
expect_contains("an edit that raises a rule's count is denied, and names the new line",
                "code_quality:CQ001 at flat.py:2", c.reason())

c = Case("eslint-project-warns")
c.file("eslint.config.js", "export default [];\n")
c.hook(c.write("a.ts", "var x = 1\n"), ESLINT_JSON=NO_VAR_ROW.replace('"severity":2', '"severity":1'))
expect_equal("a rule the project's eslint config sets to warn does not deny", "", c.decision())
c.file("a.ts", "var x = 1\n")
c.hook(c.tool("PostToolUse", "Write", "a.ts"), ESLINT_JSON=NO_VAR_ROW.replace('"severity":2', '"severity":1'))
expect_contains("and arrives as a warning", "[ts.binding.no-var] warn: eslint:no-var at a.ts:1", c.context())

c.hook(c.write("b.ts", "var x = 1\n"), ESLINT_JSON='[{"messages":[{"ruleId":"no-var-requires","line":1,"severity":2}]}]')
expect_equal("an eslint rule id matches exactly, not by prefix", ["", False],
             [c.decision(), "no-var-requires" in c.stdout])

c = Case("ruff-reselect")
c.file("ruff.toml", '[lint]\nignore = ["ALL"]\nselect = ["F403"]\n')
c.hook(c.write("app.py", "from os import *\n"), RUFF_JSON=F403_ROW)
expect_equal("a rule the project ignores with ALL but selects again still denies", "deny", c.decision())
expect_equal("ignored rules are left to ruff's own config, not selected",
             f"check --verbose --force-exclude --preview --output-format json --stdin-filename {c.project}/app.py -",
             c.args().splitlines()[-1])

c = Case("ruff-extends")
c.file("ruff.toml", 'extend = "base.toml"\n')
c.file("base.toml", '[lint]\nignore = ["F403"]\n')
c.hook(c.write("app.py", "from os import *\n"))
expect_lacks("a rule ignored in a config the project extends is left to ruff", "F403", c.args().splitlines()[-1])
c.file("ruff.toml", 'extend = "base.toml"\npreview = false\n')
c.hook(c.write("app.py", "x = 1\n"))
expect_lacks("a project that sets preview keeps its setting", "--preview", c.args().splitlines()[-1])
c.hook(c.write("app.py", "x = [a for b in c for a in b]\n"))
expect_lacks("a Python edit names no C# tool", "roslyn", c.stdout)
expect_lacks("or GDScript tool", "gdlint", c.stdout)

c = Case("ruff-narrower-ignore")
c.file("ruff.toml", '[lint]\nignore = ["PTH123"]\n')
c.hook(c.write("app.py", "x = 1\n"), PSTACK_GUIDELINES_DIR=str(PLUGIN / "skills" / "principle-code-quality" / "guidelines"))
expect_contains("a narrower project ignore stays ignored", "--extend-ignore PTH123", c.args().splitlines()[-1])
expect_contains("and the rest of the guideline code still runs", "PTH,", c.args().splitlines()[-1])
c.file("ruff.toml", '[lint]\nselect = ["PTH123"]\nignore = ["PTH123"]\n')
c.hook(c.write("app.py", "x = 1\n"), PSTACK_GUIDELINES_DIR=str(PLUGIN / "skills" / "principle-code-quality" / "guidelines"))
expect_contains("an ignore wins a tie with a select in one config, as in ruff", "--extend-ignore PTH123",
                c.args().splitlines()[-1])
c.file("ruff.toml", '[lint]\nignore = ["PTH1"]\nextend-select = ["PTH123"]\n')
c.hook(c.write("app.py", "x = 3\n"), PSTACK_GUIDELINES_DIR=str(PLUGIN / "skills" / "principle-code-quality" / "guidelines"))
expect_contains("a rule selected again inside an ignored prefix is selected on the command line too",
                ",PTH123 --extend-ignore PTH1 ", c.args().splitlines()[-1])
c.file("base.toml", '[lint]\nselect = ["ALL"]\n')
c.file("ruff.toml", 'extend = "base.toml"\n[lint]\nselect = ["E"]\n')
c.hook(c.write("app.py", "x = 4\n"), PSTACK_GUIDELINES_DIR=str(PLUGIN / "skills" / "principle-code-quality" / "guidelines"))
expect_contains("a child select resets the base's ALL, so guideline codes are added", "F403", c.args().splitlines()[-1])
c.file("base.toml", '[lint]\nignore = ["PTH123"]\n')
c.file("ruff.toml", 'extend = "base.toml"\n[lint]\nselect = ["F"]\n')
c.hook(c.write("app.py", "x = 5\n"), PSTACK_GUIDELINES_DIR=str(PLUGIN / "skills" / "principle-code-quality" / "guidelines"))
expect_lacks("and drops the base's ignores", "--extend-ignore", c.args().splitlines()[-1])
c.file("base.toml", '[lint]\nignore = ["PTH123"]\n')
c.file("ruff.toml", 'extend = "base.toml"\n[lint]\nextend-select = ["PTH123"]\n')
c.hook(c.write("app.py", "x = 2\n"), PSTACK_GUIDELINES_DIR=str(PLUGIN / "skills" / "principle-code-quality" / "guidelines"))
expect_lacks("a rule the extending config selects again is not ignored", "--extend-ignore",
             c.args().splitlines()[-1])

c = Case("ruff-python-only")
c.file("eslint.config.js", "export default [];\n")
(c.project / "app.js").write_text("")
c.hook(c.tool("PostToolUse", "Write", "app.js"))
expect_equal("ruff does not run on a JavaScript file", "", c.args())

c = Case("tool-installed-later")
(BIN / "ruff").unlink()
c.hook(c.write("app.py", "from os import *\n"), RUFF_JSON=F403_ROW)
expect_equal("missing ruff does not deny", "", c.decision())
install_stub("ruff", RUFF_STUB)
c.hook(c.write("app.py", "from os import *\n"), RUFF_JSON=F403_ROW)
expect_equal("a tool installed later in the session is found on the next call", "deny", c.decision())

c = Case("neutral")
neutral = {"kind": "pre_write", "session": "n1", "agent": "main", "cwd": str(c.project), "root": str(c.project),
           "files": [{"path": "pages.py", "before": None, "after": PAGES}]}
c.engine("--harness", "neutral", stdin=json.dumps(neutral))
expect_json("the neutral core returns the deny text", {"deny": PAGES_REASON, "context": None, "notice": None}, c.stdout)
neutral = {**neutral, "channel": False, "session": "n2", "files": [{"path": "pages.py", "before": None, "after": "x = 1\n"}]}
c.engine("--harness", "neutral", stdin=json.dumps(neutral))
expect_json("with no context channel the globals wait", {"deny": None, "context": None, "notice": None}, c.stdout)
c.engine("--harness", "neutral", stdin=json.dumps({**neutral, "channel": True, "kind": "post_write"}))
expect_equal("and arrive on the next call that has one", GLOBALS_CONTEXT, json.loads(c.stdout)["context"])

c = Case("check")
c.file("pages.py", PAGES)
c.engine("check", "pages.py")
expect_equal("check exits 1 on a block finding", 1, c.status)
expect_equal("check prints findings and guidelines, with no announcement", f"""[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:2
{ONE_FOR}

[py.comprehension.no-nested-call] warn: code_quality:CQ002 at pages.py:2
{NESTED_CALL}

[py.data.dataclass-over-dict] warn
{DATACLASS}

{OVERRIDE}
""", c.stdout)
c.file("pages.py", EXPLICIT_LOOP)
c.engine("check", "pages.py")
expect_equal("check exits 0 on a clean file", 0, c.status)
c.file("build/b.py", PAGES)
c.engine("check", "gone.py", "build/b.py", "pages.py")
expect_equal("check exits 3 on a missing path", 3, c.status)
expect_contains("check names the missing path", "Notice: did not check gone.py: no such file", c.stdout)
expect_contains("check names an excluded path",
                "Notice: did not check build/b.py: it is in a dependency or build directory", c.stdout)
c.engine("check", "build", "nope.txt")
expect_equal("check exits 3 on a directory", 3, c.status)
expect_contains("check names a directory", "Notice: did not check build: it is a directory", c.stdout)
expect_contains("check names a missing file of any type", "Notice: did not check nope.txt: no such file", c.stdout)
os.mkfifo(c.project / "queue.py")
c.engine("check", "queue.py")
expect_equal("check exits 3 on a special file", 3, c.status)
expect_contains("check names a special file", "Notice: did not check queue.py: it is not a regular file", c.stdout)
c.engine("--harness", "unknown")
expect_equal("a usage error never exits 2, which Codex reads as a block", 64, c.status)

c = Case("truncated")
guideline("py-types-mypy.md", "Type every function.", "id: py.types.mypy", "languages: python",
          "scope: contextual", "severity: warn", "enabled: true", "detectors: mypy:X")
MANY = [f"x{i} = [a for b in c for a in b]" for i in range(1, 401)]
c.hook(c.write("many.py", "\n".join(MANY)))
expect_contains("findings past the size cap are counted",
                "more findings did not fit in this message. Run the check command on many.py to see all of them.",
                c.reason())
expect_contains("a denial full of findings still names the detector that did not run",
                "Notice: mypy has no runner yet, so detectors mypy:X did not run.", c.reason())
expect_contains("and still announces the guidelines", announce("py.comprehension.one-for"), c.reason())
expect_equal("the denial stays inside the size cap", True, len(c.reason()) < 9000)
c.file("many.py", lines(*MANY))
c.engine("check", "many.py")
expect_equal("check shows every finding", 400, c.stdout.count("\n[py.comprehension.one-for] block") + c.stdout.startswith("[py.comprehension.one-for] block"))
long = "n" * 160
patch = "*** Begin Patch\n*** Update File: many.py\n@@\n-x1 = [a for b in c for a in b]\n+x1 = [a for b in c for a in b]"
for i in range(1, 50):
    c.file(f"{long}_{i}.py", b"x = 1\xff\n")
    patch += f"\n*** Update File: {long}_{i}.py\n@@\n-x = 1\n+x = 2"
c.hook(c.patch("PostToolUse", patch), harness="codex")
expect_contains("a context full of notices still counts the findings", "more findings did not fit", c.context())
expect_equal("and stays inside the size cap", True, len(c.context()) <= 9000)
wide = "w" * 220
added = "*** Begin Patch" + "".join(
    f"\n*** Add File: {name}{wide}.py\n" + "\n".join(f"+{row}" for row in MANY) for name in "abc")
c.hook(c.patch("PreToolUse", added + patch.removeprefix("*** Begin Patch")), harness="codex")
expect_contains("a denial with dropped findings counts the notices left out", "more notices did not fit", c.reason())
expect_equal("and stays inside the size cap", True, len(c.reason()) < 9000)
expect_contains("the dropped-findings notice names only whole files",
                f"Run the check command on a{wide}.py, b{wide}.py and 1 more files to see all of them.", c.reason())
spread = "*** Begin Patch" + "".join(f"\n*** Add File: clean{i}.py\n+x = 1" for i in range(1, 51))
spread += "\n*** Add File: last.py\n+x = [a for b in c for a in b]"
c.hook(c.patch("PreToolUse", spread), harness="codex")
expect_contains("files past the per-call limit are counted",
                "Notice: did not check 1 more files: a hook call checks at most 50. Run the check command on last.py.",
                c.context())
for i in range(1, 51):
    c.file(f"clean{i}.py", "x = 1\n")
c.engine("check", *(f"clean{i}.py" for i in range(1, 51)), "missing51.py")
expect_contains("check has no file limit", "Notice: did not check missing51.py: no such file", c.stdout)
c.hook({"hook_event_name": "PreToolUse", "tool_name": "Write", "cwd": str(c.project),
        "tool_input": {"file_path": "bulk.py", "content": "x" * 16_000_001}})
expect_json("an oversized payload is named, not dropped", {"systemMessage": (
    "pstack guideline hook skipped this call: its input is larger than 16 MB, so code-quality guidelines were not checked.")},
    c.stdout)

c = Case("huge-guideline")
saved = (FIXTURES / "py-comprehension-one-for.md").read_text()
guideline("py-comprehension-one-for.md", "x" * 8400, "id: py.comprehension.one-for", "languages: python",
          "scope: contextual", "severity: block", "enabled: true", "detectors: code_quality:CQ001")
c.hook(c.write("pages.py", PAGES))
expect_contains("a denial whose guideline does not fit still names the rule and line",
                "[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:2", c.reason())
expect_contains("a denial keeps the detector-unavailable notice",
                "Notice: mypy has no runner yet, so detectors mypy:X did not run.", c.reason())
expect_equal("and stays inside the size cap", True, len(c.reason()) < 9000)
(FIXTURES / "py-comprehension-one-for.md").write_text(saved)
(FIXTURES / "py-types-mypy.md").unlink()

shutil.rmtree(WORK)
print(f"{Path(__file__).name}: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
