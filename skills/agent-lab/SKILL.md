---
name: agent-lab
description: Give an agent its own throwaway podman container holding a private clone of a repo, published ports, and a virtual display it can screenshot. Use when work must not touch the real checkout, when several agents each need their own working tree and ports on one machine, when a test or a migration writes into the repo, or when a windowed app must run and be screenshotted with no desktop available. Covers environment profiles supplied as directories on disk, idempotent bring-up, port publishing, screenshots with a blankness check, and teardown.
---

# Agent lab

`scripts/lab` gives you a container with the repository mounted read-only at
`/src-ro` and a private writable clone at `/work/<repo>`. Nothing you do
inside can write the real checkout.

Paths below are relative to this skill's base directory, which the skill
loader prints when it loads this file. Prefix every `lab` command with it.

Requirements: podman, and Python 3.11 or later. No pip packages, no
environment variables to set, ever. Every knob is a flag.

## When to use it

- Work that must not touch the real checkout: a destructive migration, a
  `git reset --hard`, a test that writes into the repository.
- Several agents that each need their own working tree, ports, and caches.
- A windowed app you must run and screenshot with no desktop available.

Skip it for read-only inspection, and for anything whose answer depends on
how frames actually look. See [Limits](#limits).

## Bring a lab up

```
scripts/lab up demo --repo /path/to/repo
```

`up` converges. It builds the image if the profile changed, creates and
starts the container if the spec changed, checks the branch out, runs the
profile's setup hook, and waits for the profile's ready check. Run it twice
and the second run prints `changed=0` and rebuilds nothing.

It prints one line on stdout. Progress goes to stderr.

```
lab name=demo container=lab-demo image=agent-lab/base:latest work=/work/myrepo head=1a2b3c4d changed=4
```

Flags:

- `--repo PATH` the repository to mount and clone. Defaults to the working
  directory's repository.
- `--profile NAME` which environment. Defaults to `base`: git, python3,
  build-essential, curl, jq, Xvfb, ImageMagick, and Mesa software GL. Any
  other name is a directory you wrote. See
  [the profile contract](references/profile-contract.md).
- `--branch BRANCH` the branch to check out. Defaults to the repository's
  current branch. `up` resets that branch to the host's head, discarding
  commits made inside the container on the same branch, so push
  container-side work to a different branch name if you want it to survive.
- `--port N` override the port the profile publishes. Give each lab its own
  port: two labs cannot publish the same host port, and the second `up`
  fails at start.

## Run a command

```
scripts/lab exec demo pytest -q
```

The working directory is the private clone, so you never write `cd`.
Arguments after the lab name are passed through unparsed, and `exec` returns
the command's own exit code. For a pipeline, ask for a shell yourself:

```
scripts/lab exec demo bash -lc 'make 2>&1 | tail -40'
```

## Take a screenshot

To run a windowed command on a throwaway virtual display and photograph it:

```
scripts/lab shot demo --seconds 60 -- myapp --fullscreen
```

To photograph the display a profile's setup hook already started, and leave
whatever is running on it alone, drop the `--` and everything after it:

```
scripts/lab shot demo
```

Either form copies the PNG to the host and prints one line:

```
shot path=/path/to/repo/.nikki-agents/lab/shots/demo-2026-09-12T14-03-11Z.png size=1280x720 stddev=10497.7 colors=4093 bytes=223095
```

`--out PATH` names the file yourself. The default lands under the
repository's `.nikki-agents/lab/shots/` directory with a UTC timestamp, so
repeated shots never overwrite each other.

**Judge the frame from `stddev` and `colors`. Do not open the PNG**, because
its pixels then sit in your context for the rest of the session. A blank
display reads `stddev=0 colors=1`, and `shot` exits 1 on it rather than
reporting success. Pass `--allow-blank` when a blank frame is the answer you
wanted.

## Tear a lab down

```
scripts/lab down demo
```

This deletes the container and its `lab-demo-work` volume. The clone and any
uncommitted work in it are gone. Commit inside the container and fetch from
the host first if you want to keep anything.

To see which labs exist, ask podman:

```
podman ps -a --filter label=lab.spec
```

## Check the host before you trust it

```
scripts/lab check --profile base
```

`check` prints one `ok:` or `FAIL:` line per check and exits 1 if any
failed. It confirms podman answers, the profile resolves and its
`profile.json` parses, and the repository's head resolves. It builds nothing.
Run it first on a machine you have not used before, and after editing a
profile.

## One lab per parallel candidate

Bring up one lab per candidate, named for the candidate, from the same
repository. Give each its own branch and its own port, collect results as
text, and tear each one down when its verdict is in.

```
scripts/lab up cand-a --repo /path/to/repo --branch feat/cand-a --port 6551
scripts/lab up cand-b --repo /path/to/repo --branch feat/cand-b --port 6552
scripts/lab exec cand-a ./run-gate.sh
scripts/lab down cand-a
```

## Limits

- **No GPU.** Rendering is llvmpipe and lavapipe on the CPU. No visual
  judgment happens here. Anything that turns on how frames actually look
  stays on a real display.
- **No real desktop.** Xvfb is a headless X server. There is no compositor,
  no window manager, and no host display is ever mounted.
- **No writes to the real checkout.** By design. Get work out with git inside
  the container, or with `podman cp`.
- **podman only.** docker is not supported and is not detected. One engine
  means one code path in every call site, and "works anywhere podman works"
  already includes macOS, where podman runs a Linux VM.
- **On macOS**, the repository must sit inside a directory the podman machine
  shares, `$HOME` by default. A bind mount of an unshared path mounts nothing
  and fails confusingly later. A profile that fetches an x86_64 binary also
  needs an arm64 build or emulation on Apple Silicon.
- **Rootless podman** cannot publish a port below 1024, and has no
  `/dev/dri`, so software GL is the only GL.
