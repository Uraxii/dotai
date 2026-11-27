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
sys.stdin.read()
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
with open(os.path.join(os.environ["WORK"], "eslint.args"), "a") as args:
    args.write(" ".join(sys.argv[1:]) + "\\n")
sys.stdin.read()
print(os.environ.get("ESLINT_JSON") or '[{{"messages":[]}}]')
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
    f"check --isolated --line-length 80 --select F403 --output-format json --stdin-filename {c.project}/tests/test_app.py -\n"
    f"check --isolated --line-length 80 --select F403,S101 --output-format json --stdin-filename {c.project}/src/app.py -"),
    c.args())

c = Case("disabled")
c.hook(c.write("src/app.py", 'print("x")\n'), RUFF_JSON='[{"code":"T201","location":{"row":1}}]')
expect_equal("a disabled guideline's detector is not selected",
             f"check --isolated --line-length 80 --select F403,S101 --output-format json --stdin-filename {c.project}/src/app.py -",
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
c.hook(c.write("src/app.py", "from os import *\n"), RUFF_JSON=F403_ROW)
expect_equal("a rule the project ignores does not block", "", c.decision())
expect_lacks("a rule the project ignores gives no finding", "py.import.no-star", c.stdout)
expect_equal("ruff runs with the project config, without the ignored rule",
             f"check --verbose --force-exclude --extend-select S101 --output-format json --stdin-filename {c.project}/src/app.py -",
             c.args().splitlines()[-1])
c.hook(c.write("src/dist/app.py", "assert x\n"), RUFF_JSON=F403_ROW,
       RUFF_STDERR='DEBUG Ignored path via `exclude`: "src/dist"')
expect_equal("a file ruff's config excludes does not deny", "", c.decision())
expect_contains("and the user is told ruff skipped it",
                "Notice: ruff skips this file under its exclude settings (the project's or ruff's defaults), so detectors ruff:S101 did not run.",
                c.context())
c.hook(c.tool("PostToolUse", "Write", "src/app.py"), RUFF_JSON=F403_ROW)
expect_lacks("the ignored rule stays quiet after the write", "py.import.no-star", c.stdout)
two = WORK / "two-detectors"
shutil.copytree(FIXTURES, two)
no_star = two / "py-import-no-star.md"
no_star.write_text(no_star.read_text().replace("detectors: ruff:F403\n", "detectors: ruff:F403, code_quality:CQ001\n"))
(two / "py-comprehension-one-for.md").unlink()
c.hook(c.write("src/two.py", "x = [a for b in c for a in b]\n"), PSTACK_GUIDELINES_DIR=str(two), RUFF_JSON=F403_ROW)
expect_contains("an ignored detector leaves the guideline's other detectors on",
                "[py.import.no-star] block: code_quality:CQ001 at src/two.py:1", c.reason())
expect_lacks("the ignored detector gives no finding", "ruff:F403 at", c.reason())

c = Case("project-pyproject")
c.file("pyproject.toml", '[tool.ruff.lint.per-file-ignores]\n"src/*" = ["F403"]\n')
c.hook(c.write("src/app.py", "from os import *\n"), RUFF_JSON=F403_ROW)
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

NO_VAR_ROW = '[{"messages":[{"ruleId":"no-var","line":1}]}]'
c = Case("eslint-no-config")
c.hook(c.write("a.ts", "var x = 1\n"), ESLINT_JSON=NO_VAR_ROW)
expect_contains("eslint does not run without a project config",
                "Notice: eslint has no project config, so detectors eslint:no-var did not run.", c.context())
expect_equal("eslint was not started", "", c.args("eslint"))

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
OLD_PYTHON = ("import runpy, sys; sys.version_info = (3, 10); sys.argv = [sys.argv[1], 'claude']; "
              "runpy.run_path(sys.argv[0], run_name='__main__')")
c.run([sys.executable, "-c", OLD_PYTHON, str(HOOK)], json.dumps(c.session_start("startup")), {"PATH": str(EMPTY)})
expect_equal("without Python 3.11 the session start tells the user", PYTHON_NOTICE, c.message())
expect_equal("and tells the agent", PYTHON_NOTICE, c.context())
c.run([sys.executable, "-c", OLD_PYTHON, str(HOOK)], json.dumps(c.write("pages.py", PAGES)), {"PATH": str(EMPTY)})
expect_equal("without Python 3.11 other hooks stay quiet", "0:", f"{c.status}:{c.stdout}")
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


def chain(harness, last="true"):
    return ('for python in python3 python3.14 python3.13 python3.12 python3.11 python; do '
            'command -v "$python" >/dev/null 2>&1 && '
            f'exec "$python" -I "${{CLAUDE_PLUGIN_ROOT}}/hooks/guidelines.py" {harness}; done; {last}')


NO_PYTHON_JSON = json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": PYTHON_NOTICE},
                             "systemMessage": PYTHON_NOTICE})
CLAUDE_START = chain("claude", f"printf '%s\\n' '{NO_PYTHON_JSON}'")
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
expect_equal("with no Python on PATH other wired hooks exit 0 quietly", "0:", f"{c.status}:{c.stdout}")
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
ENGINE_DATA = WORK / "engine-data"
c.run(CLAUDE_START, json.dumps(c.session_start("startup")), {"CLAUDE_PLUGIN_DATA": str(ENGINE_DATA)})
expect_equal("the engine's new data folders are private to the user", ["0o700", "0o700"],
             [oct(path.stat().st_mode & 0o777) for path in (ENGINE_DATA, ENGINE_DATA / "guideline-state")])

CODEX_COMMAND = chain("codex")
CODEX_START = chain("codex", f"printf '%s\\n' '{NO_PYTHON_JSON}'")
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
