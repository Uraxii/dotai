# Why podman-sandbox is shaped this way

This skill was called `agent-lab` until the name changed to say which
container tool it needs. The `lab` command kept its name.

The previous version was 449 lines of code, 361 of them bash, and adding an
environment meant editing a `case` statement inside the skill. This version
keeps the three properties that earned their place and deletes the rest.

## Kept, because each one earns it

**Idempotent converge.** An agent re-running `up` must not pay for a rebuild.
`changed=N` on the output line is the proof. The hash now covers the whole
profile directory rather than one Containerfile, because a profile is a
directory whose setup script is as load-bearing as its recipe.

**A named volume for the clone, not a host bind mount.** This sidesteps uid
mapping entirely and makes it impossible for a container to leave a file on
the host it owns. The cost is that `down` destroys the clone, which is
correct for a throwaway lab.

**Ports pinned to loopback.** `127.0.0.1:<port>:<port>`, so nothing on the
local network reaches a lab.

**Screenshot statistics instead of the image.** `stddev` and `colors` tell a
rendered frame from a blank one in two numbers, and they cost an agent no
context. Opening a PNG costs it for the rest of the session.

## Cut

| Cut | Why |
| --- | --- |
| docker support, engine detection, `--engine` | One engine is one code path in every call site. "Works anywhere podman works" is already the portability bar. |
| `pull NAME BRANCH` | `up NAME --branch B` does the same thing idempotently. `pull` existed only to skip image work that `up` already hash-skips, and it re-parsed the spec label to rediscover the repo. |
| `ls` | `podman ps -a --filter label=lab.spec` is one documented line and gives a human real podman output to pipe. A wrapper added a subcommand and hid the filter. |
| `selftest`'s engine dry-run | It existed to test the docker path on a machine with no docker. With one engine it has nothing to prove. `check` replaces it with preflight checks that fail loudly before a build. |
| `--editor`, and roughly 60 lines of Godot logic | A profile's `setup` and `ready` hooks cover it, in two JSON keys. The skill now holds zero lines about any one application. |
| `godot_version.py` and `GODOT_4_7_2_BIN` | Both depended on a binary in the author's home directory, so neither worked on any other machine. A profile fetches its own tools from upstream. |
| `references/proxmox-overflow.md` | 81 lines of prose for a feature with no implementing code. |
| `ARG`/`LABEL` boilerplate in every Containerfile | The recipe hash arrives as `podman build --label`, so a user's Containerfile carries no lab-specific lines at all. |
| `x11-apps`, `xdotool`, `libasound2t64`, `libpulse0` from `base` | No code called any of them. |

## Fixed by structure, not by care

**Command injection.** The old `sync_repo` interpolated a user-supplied
branch name into a remote `bash -lc` string. Every subprocess call in this
version takes a `list[str]`, `shell=True` appears nowhere, and the invariant
is stated in `lab_container.py`'s module docstring. A caller who wants a
shell passes `["bash", "-lc", script]` and owns that script.

**A blank screenshot reported as a success.** `shot` exits 1 when `stddev` is
0. The previous version printed the numbers and trusted the caller to read
them.

**A screenshot killing a running editor.** `lab-shot` used to take display
`:99` over, tearing down the editor it was photographing. The throwaway
display is now `:100` and the persistent one stays `:99`, so the two modes
cannot collide.

**State drifting from reality.** State is one podman label, `lab.spec`, not a
file. A label is created with the container and dies with it, so the tool
cannot believe in a lab somebody removed by hand. A state file would need
reconciliation code that a label makes unnecessary.

## Declared in JSON, not in image labels

A profile could have declared its port and hooks as `LABEL` lines in its own
Containerfile instead of a `profile.json` beside it. JSON won for three
reasons. A label holds only a string, so an argument list would have to be
encoded as a shell-like string and re-split, which is the injection this
design removes. Labels must be re-declared in every derived Containerfile,
which is the `ARG`/`LABEL` repetition already being deleted. And reading a
label requires building the image first, so the tool could not know which
port to publish until after the build.

## Size, measured

Two numbers, because they say different things. "Code" counts lines that are
neither blank, a comment, nor part of a docstring, which is the code a reader
has to follow. "Statements" counts syntax statements, which ignores how far a
call is wrapped to fit the line limit. "Total" counts every line, docstrings
included. The old version's 449 was almost all code lines: bash carried its
contracts in prose at the top of one file, not next to each function.

| File | Code | Statements | Total |
| --- | --- | --- | --- |
| `scripts/lab` | 220 | 188 | 395 |
| `scripts/lab_container.py` | 165 | 143 | 338 |
| `scripts/lab_profile.py` | 122 | 97 | 214 |
| `profiles/base/lab-shot` | 24 | 24 | 45 |
| `profiles/base/Containerfile` | 18 | 18 | 25 |
| Total | 549 | 470 | 1017 |

The design projected 310 code lines and the implementation landed on 549.
Three things account for the gap, and none of them is a feature the design
did not ask for. Python wraps: an argument list that bash writes on one line
takes three or four inside an 80 column limit, which is why the statement
count, 470, sits so much closer to the projection than the line count does.
argparse costs about 30 lines for five subcommands and their flags, which the
projection did not price. And each untyped boundary, `profile.json` and the
identify line `lab-shot` prints, pays for a parse function that rejects bad
input rather than trusting it.

Against 449 lines before: more lines, fewer moving parts. One engine instead
of two, five subcommands instead of seven, no application-specific code at
all, and no shell string built from user input anywhere.

## What the implementation settled

**A sentinel file records that setup ran, not a field on the spec.** A podman
label cannot be changed after the container is created, so a
`setup_sha256` field on `LabSpec` could only be written before setup ran,
which is a lie the next `up` would believe. `/work/.lab-setup-<recipe hash>`
sits in the volume beside the clone that setup mutated: it dies with that
clone on `down`, and its name changes when the profile changes, so editing a
setup script runs it again.

**`check` does not test whether the port is free.** A port free when `check`
runs can be taken by the time `up` runs, so a green line would be a promise
the tool cannot keep. podman names the collision itself, and `up` adds the
`--port` hint to podman's own message.

**The Python floor is 3.7.** Every construct here parses under 3.7's grammar,
and the newest standard library calls used, `dataclasses` and
`subprocess.run(capture_output=True)`, both arrived in 3.7. SKILL.md said
3.11, which was a guess. The floor is not raised for convenience: nothing
here needs a newer release.

## Why `lab-shot` is bash

Every other script in this skill is Python. `lab-shot` is five `exec` calls
with no logic, and Python could only wrap each one in a `subprocess` call for
more lines. It also runs inside the container, where
requiring python3 would make every profile carry a dependency it otherwise
would not need. `"$@"` passes the caller's argument list through without a
re-parse, so the no-shell-strings invariant holds.
