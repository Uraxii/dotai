import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


HOOK_PATH = Path(__file__).resolve().parents[1] / "opus_5_reduce_output.py"
PLUGIN_ROOT = HOOK_PATH.parents[1]
SPEC = importlib.util.spec_from_file_location("opus_5_reduce_output", HOOK_PATH)
HOOK = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(HOOK)


def assistant(model="claude-opus-5", tools=(), sidechain=False):
    return {
        "type": "assistant",
        "isSidechain": sidechain,
        "message": {
            "model": model,
            "content": [
                tool
                if isinstance(tool, dict)
                else {"type": "tool_use", "name": tool}
                for tool in tools
            ],
        },
    }


def bash(command):
    return {"type": "tool_use", "name": "Bash", "input": {"command": command}}


def user_prompt(text="do the thing"):
    return {"type": "user", "message": {"content": text}}


def tool_result(tool_use_id="toolu_first"):
    """A tool result. Same `type: "user"` as a prompt, not a turn boundary."""
    return {
        "type": "user",
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": "ok",
                }
            ]
        },
    }


def injected_prompt(text="Base directory for this skill: /workspace/skills/x"):
    """A harness injection, e.g. a loaded skill. Carries isMeta, not typed."""
    return {
        "type": "user",
        "isMeta": True,
        "message": {"content": [{"type": "text", "text": text}]},
    }


WORKING_TURN = [
    user_prompt(),
    assistant(tools=["Read", "Grep", "Edit", "Bash", "Edit", "Bash"]),
]


class Opus5ReduceOutputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(
            self.enterContext(tempfile.TemporaryDirectory())
        )
        # Never let a test touch the user's real ~/.claude/clean-recap.log,
        # and never let an ambient override decide a gate under test.
        environment = {**os.environ, "CLEAN_RECAP_LOG": str(self.log_path)}
        environment.pop("CLEAN_RECAP_MODEL_PATTERN", None)
        self.environment = environment
        self.enterContext(mock.patch.dict(os.environ, environment, clear=True))

    @property
    def log_path(self) -> Path:
        return self.directory / "clean-recap.log"

    def transcript(self, name: str, entries: list[dict]) -> str:
        path = self.directory / f"{name}.jsonl"
        path.write_text(
            "\n".join(json.dumps(entry) for entry in entries) + "\n",
            encoding="utf-8",
        )
        return str(path)

    def decide(self, payload: dict) -> str:
        """Run the hook's main() on a Stop envelope; "block" or "allow"."""
        stdout = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(json.dumps(payload))):
            with redirect_stdout(stdout):
                exit_code = HOOK.main()

        self.assertEqual(0, exit_code, "a Stop hook must always exit 0")
        printed = stdout.getvalue().strip()
        if not printed:
            return "allow"
        self.assertEqual(
            {"decision": "block", "reason": HOOK.RECAP_INSTRUCTION},
            json.loads(printed),
        )
        return "block"

    # -- manifest wiring ---------------------------------------------------

    def test_claude_manifest_installs_the_stop_hook_without_a_matcher(
        self,
    ) -> None:
        config = json.loads(
            (PLUGIN_ROOT / "hooks" / "hooks.json").read_text()
        )

        stop_entries = config["hooks"]["Stop"]
        # One entry only: a duplicated Stop key silently loses a hook.
        self.assertEqual(1, len(stop_entries))
        stop_entry = stop_entries[0]
        # Stop is not tied to a tool, so it takes no matcher.
        self.assertNotIn("matcher", stop_entry)
        hook = stop_entry["hooks"][0]
        self.assertEqual("command", hook["type"])
        self.assertEqual(
            "${CLAUDE_PLUGIN_ROOT}/hooks/opus_5_reduce_output.py", hook["command"]
        )
        self.assertEqual(10, hook["timeout"])
        self.assertTrue(HOOK_PATH.is_file())
        self.assertTrue(os.access(HOOK_PATH, os.X_OK))

    def test_sibling_manifests_do_not_install_the_stop_hook(self) -> None:
        # Codex documents no turn-end event, and Copilot's agentStop envelope
        # is camelCase, so its stopHookActive loop guard would never trip.
        self.assertFalse((PLUGIN_ROOT / "hooks" / "codex-hooks.json").exists())
        self.assertFalse((PLUGIN_ROOT / "hooks.json").exists())

    def test_recap_instruction_has_no_em_dash(self) -> None:
        self.assertNotIn("—", HOOK.RECAP_INSTRUCTION)

    # -- the gate ----------------------------------------------------------

    def test_fresh_turn_of_real_work_blocks(self) -> None:
        payload = {"transcript_path": self.transcript("work", WORKING_TURN)}

        self.assertEqual("block", self.decide(payload))
        self.assertIn("BLOCK", self.log_path.read_text(encoding="utf-8"))

    def test_a_turn_with_no_tool_calls_at_all_skips(self) -> None:
        """A turn that ran nothing changed nothing, so it has no recap."""
        entries = [user_prompt(), assistant(tools=[])]

        self.assertEqual(
            "allow",
            self.decide({"transcript_path": self.transcript("idle", entries)}),
        )

    def test_a_read_only_turn_skips(self) -> None:
        entries = [user_prompt(), assistant(tools=["Read"] * 8)]

        self.assertEqual(
            "allow",
            self.decide({"transcript_path": self.transcript("read", entries)}),
        )

    def test_a_two_tool_turn_asks_for_a_recap(self) -> None:
        """Replaces the old tool-call floor case. There is no floor."""
        entries = [user_prompt(), assistant(tools=["Edit", "Bash"])]

        self.assertEqual(
            "block",
            self.decide({"transcript_path": self.transcript("small", entries)}),
        )

    # -- the mutation gate -------------------------------------------------

    def test_a_turn_of_one_read_only_shell_command_skips(self) -> None:
        """The reported bug. One read-only command and an answer got a recap
        that only restated a reply already short and plain."""
        entries = [
            user_prompt("which python is on PATH?"),
            assistant(tools=[bash("which python3")]),
        ]

        self.assertEqual(
            "allow",
            self.decide({"transcript_path": self.transcript("look", entries)}),
        )
        self.assertIn(
            "turn used no mutating tool",
            self.log_path.read_text(encoding="utf-8"),
        )

    def test_a_turn_containing_an_edit_asks_for_a_recap(self) -> None:
        entries = [
            user_prompt(),
            assistant(tools=[bash("rg todo"), "Edit"]),
        ]

        self.assertEqual(
            "block",
            self.decide({"transcript_path": self.transcript("edit", entries)}),
        )

    def test_a_turn_containing_a_mutating_shell_command_asks_for_a_recap(
        self,
    ) -> None:
        entries = [
            user_prompt(),
            assistant(tools=[bash("rm -rf /workspace/build")]),
        ]

        self.assertEqual(
            "block",
            self.decide({"transcript_path": self.transcript("rm", entries)}),
        )

    def test_a_turn_that_spawned_an_agent_asks_for_a_recap(self) -> None:
        """A delegate's own edits never reach this transcript, so a turn
        that spawned one is assumed to have changed something."""
        entries = [user_prompt(), assistant(tools=["Agent"])]

        self.assertEqual(
            "block",
            self.decide({"transcript_path": self.transcript("agent", entries)}),
        )

    def test_a_turn_containing_a_multi_edit_asks_for_a_recap(self) -> None:
        entries = [user_prompt(), assistant(tools=["MultiEdit"])]

        self.assertEqual(
            "block",
            self.decide({"transcript_path": self.transcript("multi", entries)}),
        )

    def test_a_turn_that_resumed_a_delegate_asks_for_a_recap(self) -> None:
        """SendMessage makes a live delegate work, on the same argument that
        puts Agent and Task here. Its edits never reach this transcript."""
        entries = [user_prompt(), assistant(tools=["SendMessage"])]

        self.assertEqual(
            "block",
            self.decide({"transcript_path": self.transcript("resume", entries)}),
        )

    def test_a_turn_that_spawned_a_task_asks_for_a_recap(self) -> None:
        entries = [user_prompt(), assistant(tools=["Task"])]

        self.assertEqual(
            "block",
            self.decide({"transcript_path": self.transcript("task", entries)}),
        )

    def test_tool_results_do_not_truncate_the_turn(self) -> None:
        """Boundary-detection guard. A tool result is `type: "user"` too.
        Mistaking one for a prompt cuts the turn at its first tool call, so
        the mutating command later in the turn would go unseen."""
        entries = [
            user_prompt(),
            assistant(tools=[bash("cat /workspace/notes.md")]),
            tool_result(),
            assistant(tools=[bash("git commit -m 'save the notes'")]),
        ]

        self.assertEqual(
            "block",
            self.decide({"transcript_path": self.transcript("chain", entries)}),
        )

        # The mutation has to sit on the far side of the tool result too:
        # a boundary mistake truncates to the tail, which reads clean.
        entries = [
            user_prompt(),
            assistant(tools=[bash("git commit -m 'save the notes'")]),
            tool_result(),
            assistant(tools=[bash("git show --stat HEAD")]),
        ]

        self.assertEqual(
            "block",
            self.decide({"transcript_path": self.transcript("tail", entries)}),
        )

    def test_an_injected_prompt_does_not_truncate_the_turn(self) -> None:
        """A loaded skill arrives as a `type: "user"` text block with isMeta.
        It is not something the human typed, so it is not a boundary."""
        entries = [
            user_prompt(),
            assistant(tools=[bash("mkdir /workspace/out"), "Skill"]),
            injected_prompt(),
            assistant(tools=[bash("ls /workspace/out")]),
        ]

        self.assertEqual(
            "block",
            self.decide({"transcript_path": self.transcript("skill", entries)}),
        )

    def test_a_promptless_transcript_asks_for_a_recap(self) -> None:
        """A gate that cannot see the turn boundary must not suppress."""
        entries = [assistant(tools=[bash("ls /workspace")])]

        self.assertEqual(
            "block",
            self.decide({"transcript_path": self.transcript("orphan", entries)}),
        )
        self.assertIn(
            "turn boundary unknown", self.log_path.read_text(encoding="utf-8")
        )

    def test_unparseable_lines_around_the_turn_ask_for_a_recap(self) -> None:
        """Malformed lines are skipped, so the prompt is lost and the turn
        boundary is unknown. That falls through to requesting the recap."""
        path = self.directory / "garbage.jsonl"
        path.write_text(
            "not json\n"
            + json.dumps(assistant(tools=[bash("ls /workspace")]))
            + "\n{ also not json\n",
            encoding="utf-8",
        )

        self.assertEqual("block", self.decide({"transcript_path": str(path)}))
        self.assertIn(
            "turn boundary unknown", self.log_path.read_text(encoding="utf-8")
        )

    def test_a_wholly_unparseable_transcript_allows_at_the_model_gate(
        self,
    ) -> None:
        """Unchanged pre-existing behaviour. With no readable reply there is
        no model to match, so the model gate allows before the new one runs."""
        path = self.directory / "rubble.jsonl"
        path.write_text("not json\n{ also not json\n", encoding="utf-8")

        self.assertEqual("allow", self.decide({"transcript_path": str(path)}))
        self.assertIn(
            "model does not match", self.log_path.read_text(encoding="utf-8")
        )

    def test_only_the_current_turn_is_examined(self) -> None:
        """An earlier turn's edits must not keep requesting recaps forever."""
        entries = [
            user_prompt("older turn"),
            assistant(tools=["Edit", "Write"]),
            user_prompt("this turn"),
            assistant(tools=[bash("git status")]),
        ]

        self.assertEqual(
            "allow",
            self.decide({"transcript_path": self.transcript("prior", entries)}),
        )

    # -- shell command classification --------------------------------------

    def test_read_only_commands_are_not_mutations(self) -> None:
        for command in [
            "which python3",
            "ls -la /workspace",
            "git status",
            "git log --oneline -20",
            "git diff HEAD",
            "gh pr view 12",
            "rg --files-with-matches todo /workspace",
            "cat /workspace/a.txt /workspace/b.txt",
            "pytest -q 2>&1",
            "python3 -c 'print(1 >= 0)'",
            "grep -n foo /workspace/x | head -5",
            "ps aux | grep node",
            # Redirecting to /dev/null discards, it does not write.
            "python3 scripts/validate-skills.py >/dev/null 2>&1",
            "python3 scripts/validate-skills.py > /dev/null",
            "python3 scripts/validate-skills.py >>/dev/null",
            "python3 scripts/validate-skills.py >> /dev/null",
            "git rev-parse HEAD 2>/dev/null",
            # A global option before the verb does not make a read verb write.
            "git -C /workspace/wt status",
            "git --no-pager log -5",
            "gh -R owner/repo pr view 12",
            # A trailing & is a descriptor dup, not a write.
            "cmd >&2",
        ]:
            with self.subTest(command=command):
                self.assertFalse(HOOK._command_mutates(command))

    def test_mutating_commands_are_detected(self) -> None:
        for command in [
            "rm -rf /workspace/build",
            "mv /workspace/a /workspace/b",
            "cp /workspace/a /workspace/b",
            "mkdir -p /workspace/out",
            "touch /workspace/marker",
            "install -m 755 bin/tool /workspace/bin/tool",
            "ln -s /workspace/a /workspace/b",
            "sed -i 's/a/b/' /workspace/x",
            "echo hi | tee /workspace/x",
            "echo hi > /workspace/x",
            "echo hi >> /workspace/x",
            "git commit -m 'wip'",
            "git push origin develop",
            "git merge develop",
            "git rebase develop",
            "git reset --hard HEAD",
            "git checkout develop",
            "git branch -D stale",
            "git worktree add /workspace/wt develop",
            "git worktree remove /workspace/wt",
            "gh pr create --base develop",
            "gh pr merge 12",
            "sudo chmod 600 /workspace/key",
            "FOO=bar rm /workspace/x",
            # A global option between the program and its verb. This is the
            # form an agent working in a worktree actually uses.
            "git -C /workspace/wt push origin develop",
            "git -C . add -A",
            "git -C /workspace/wt worktree remove --force /workspace/gone",
            "git -c user.name=x commit -m 'wip'",
            "gh -R owner/repo pr create --base develop",
            # Redirect spellings other than a bare >.
            "make &> /workspace/build.log",
            "python3 gen.py 1> /workspace/out.txt",
            "make 2> /workspace/build.log",
            # Wrappers that run the real program.
            "env FOO=1 rm /workspace/x",
            "command rm /workspace/x",
            "find /workspace -name '*.tmp' | xargs rm -f",
        ]:
            with self.subTest(command=command):
                self.assertTrue(HOOK._command_mutates(command))

    def test_every_segment_of_a_chain_is_classified(self) -> None:
        self.assertTrue(HOOK._command_mutates("git status && git commit -m x"))
        self.assertTrue(HOOK._command_mutates("ls; rm /workspace/x"))
        self.assertTrue(
            HOOK._command_mutates("cat /workspace/a || touch /workspace/a")
        )
        self.assertFalse(HOOK._command_mutates("git status && git diff"))

    def test_the_dev_null_carve_out_does_not_swallow_a_later_write(self) -> None:
        """Excusing the discard must not excuse the rest of the line."""
        self.assertTrue(
            HOOK._command_mutates("check >/dev/null && rm -rf /workspace/d")
        )
        self.assertTrue(HOOK._command_mutates("check >/dev/null; touch /workspace/x"))
        self.assertTrue(
            HOOK._command_mutates("check >/dev/null 2>&1 > /workspace/out")
        )

    # -- loop guard --------------------------------------------------------

    def test_second_stop_allows_so_the_session_can_end(self) -> None:
        payload = {
            "stop_hook_active": True,
            "transcript_path": self.transcript("work", WORKING_TURN),
        }

        self.assertEqual("allow", self.decide(payload))
        self.assertIn("stand down", self.log_path.read_text(encoding="utf-8"))

    def test_absent_stop_hook_active_still_blocks(self) -> None:
        payload = {"transcript_path": self.transcript("work", WORKING_TURN)}

        self.assertNotIn("stop_hook_active", payload)
        self.assertEqual("block", self.decide(payload))

    def test_stop_hook_active_as_a_string_allows(self) -> None:
        payload = {
            "stop_hook_active": "true",
            "transcript_path": self.transcript("work", WORKING_TURN),
        }

        self.assertEqual("allow", self.decide(payload))

    # -- malformed input ---------------------------------------------------

    def test_empty_payload_allows(self) -> None:
        self.assertEqual("allow", self.decide({}))

    def test_missing_transcript_file_allows(self) -> None:
        self.assertEqual(
            "allow",
            self.decide({"transcript_path": str(self.directory / "gone.jsonl")}),
        )
        self.assertIn(
            "no readable transcript_path",
            self.log_path.read_text(encoding="utf-8"),
        )

    def test_transcript_path_pointing_at_a_directory_allows(self) -> None:
        self.assertEqual(
            "allow", self.decide({"transcript_path": str(self.directory)})
        )

    # -- model matching ----------------------------------------------------

    def test_unmatched_model_allows(self) -> None:
        entries = [
            user_prompt(),
            assistant(
                model="claude-sonnet-4-5",
                tools=["Read", "Edit", "Bash", "Edit", "Read", "Bash"],
            ),
        ]

        self.assertEqual(
            "allow",
            self.decide({"transcript_path": self.transcript("sonnet", entries)}),
        )
        self.assertIn(
            "model does not match", self.log_path.read_text(encoding="utf-8")
        )

    def test_fable_model_blocks(self) -> None:
        entries = [
            user_prompt(),
            assistant(
                model="claude-fable-5-1",
                tools=["Read", "Edit", "Bash", "Edit", "Read", "Bash"],
            ),
        ]

        self.assertEqual(
            "block",
            self.decide({"transcript_path": self.transcript("fable", entries)}),
        )

    def test_opus_5_model_still_blocks(self) -> None:
        entries = [
            user_prompt(),
            assistant(
                model="claude-opus-5",
                tools=["Read", "Edit", "Bash", "Edit", "Read", "Bash"],
            ),
        ]

        self.assertEqual(
            "block",
            self.decide({"transcript_path": self.transcript("opus", entries)}),
        )

    def test_sidechain_work_does_not_count(self) -> None:
        entries = [
            user_prompt(),
            assistant(
                tools=["Read", "Edit", "Bash", "Edit", "Read", "Bash"],
                sidechain=True,
            ),
        ]

        self.assertEqual(
            "allow",
            self.decide({"transcript_path": self.transcript("side", entries)}),
        )

    def test_the_model_read_is_the_one_that_answered_last(self) -> None:
        entries = [
            user_prompt("older turn"),
            assistant(model="claude-sonnet-5", tools=["Read"]),
            user_prompt("this turn"),
            assistant(model="claude-opus-5", tools=["Read"]),
        ]

        self.assertEqual(
            "claude-opus-5",
            HOOK._current_model(Path(self.transcript("order", entries))),
        )

    def test_no_assistant_reply_leaves_the_model_unknown(self) -> None:
        entries = [user_prompt("hi")]

        self.assertEqual(
            "-", HOOK._current_model(Path(self.transcript("bare", entries)))
        )

    # -- logging and real invocation ---------------------------------------

    def test_the_log_rolls_over_instead_of_growing_without_bound(self) -> None:
        # Drive the real _log() call path (through main(), not a helper)
        # past the rollover threshold repeatedly and confirm the file
        # never grows past it, and that early lines are actually gone
        # afterward -- proof of a rollover, not just a lucky small write.
        environment = {**self.environment, "CLEAN_RECAP_LOG_MAX_BYTES": "500"}
        with mock.patch.dict(os.environ, environment, clear=True):
            for _ in range(80):
                self.decide({})

        contents = self.log_path.read_text(encoding="utf-8")
        self.assertLessEqual(self.log_path.stat().st_size, 500 + 300)
        lines = contents.splitlines()
        self.assertLess(len(lines), 80, "expected old lines to be dropped")
        self.assertTrue(
            all(
                "no readable transcript_path" in line or "rolled over" in line
                for line in lines
            )
        )
        self.assertTrue(
            any("rolled over" in line for line in lines),
            "expected at least one rollover marker line",
        )

    def test_malformed_max_bytes_falls_back_to_the_default_instead_of_crashing(
        self,
    ) -> None:
        # The real-world bug: CLEAN_RECAP_LOG_MAX_BYTES=1MB used to raise
        # ValueError outside any guard, so the hook never printed its
        # block decision and a recap was silently skipped every turn.
        environment = {**self.environment, "CLEAN_RECAP_LOG_MAX_BYTES": "1MB"}
        result = subprocess.run(
            [str(HOOK_PATH)],
            input=json.dumps(
                {"transcript_path": self.transcript("work", WORKING_TURN)}
            ),
            capture_output=True,
            text=True,
            env=environment,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            {"decision": "block", "reason": HOOK.RECAP_INSTRUCTION},
            json.loads(result.stdout),
        )
        self.assertIn("BLOCK", self.log_path.read_text(encoding="utf-8"))

    def test_malformed_model_pattern_falls_back_to_the_default_instead_of_silently_skipping(
        self,
    ) -> None:
        # The same defect one env var over, quieter than the max-bytes one:
        # an invalid CLEAN_RECAP_MODEL_PATTERN used to raise inside
        # re.search with no guard, so the hook exited 0 with empty stdout
        # and no log line at all, and a recap was skipped every turn.
        environment = {**self.environment, "CLEAN_RECAP_MODEL_PATTERN": "opus-5("}
        result = subprocess.run(
            [str(HOOK_PATH)],
            input=json.dumps(
                {"transcript_path": self.transcript("work", WORKING_TURN)}
            ),
            capture_output=True,
            text=True,
            env=environment,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            {"decision": "block", "reason": HOOK.RECAP_INSTRUCTION},
            json.loads(result.stdout),
        )
        log_contents = self.log_path.read_text(encoding="utf-8")
        self.assertIn("rejected", log_contents)
        self.assertIn("BLOCK", log_contents)

    def test_every_decision_is_logged_to_the_configured_path(self) -> None:
        self.decide({"transcript_path": self.transcript("work", WORKING_TURN)})
        self.decide({})

        lines = self.log_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(2, len(lines))
        self.assertIn("BLOCK", lines[0])
        self.assertIn("allow", lines[1])

    def test_runs_as_an_executable_the_way_the_manifest_invokes_it(self) -> None:
        result = subprocess.run(
            [str(HOOK_PATH)],
            input=json.dumps(
                {"transcript_path": self.transcript("work", WORKING_TURN)}
            ),
            capture_output=True,
            text=True,
            env=self.environment,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            {"decision": "block", "reason": HOOK.RECAP_INSTRUCTION},
            json.loads(result.stdout),
        )


if __name__ == "__main__":
    unittest.main()
