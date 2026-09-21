---
name: podman-sandbox
description: Gives an agent a throwaway podman container holding a private clone of a repository, the real checkout mounted read-only, an optional published port, and a virtual display it can screenshot. Use when work must not touch the real checkout, when several agents each need their own working tree and ports on one machine, when a test or a migration writes into the repository, or when a windowed app must run and be screenshotted with no desktop available. Covers bring-up from the project's own Containerfile, running commands in the clone, port publishing, screenshots with a blankness check, rescuing commits out of a container, and teardown.
---

# Podman sandbox

`scripts/lab` gives you a container with the repository mounted read-only at `/src-ro` and a
private writable clone at `/work/<repo>`. Nothing you do inside can write the real checkout.

Paths below are relative to this skill's base directory, which the skill loader prints when it
loads this file. Prefix every `lab` command with it. Requirements: podman, and Python 3.7 or
later. No pip packages, and no environment variables to set, ever. Every knob is a flag.

The container recipe lives in one place, `<repo>/.sandbox-container/`. This skill ships no
image.

- `Containerfile` is required. The whole directory is the build context, so editing any
  file in it rebuilds the image.
- `setup` and `ready` are optional executables, found by name and run inside the
  container. `setup` runs once after the clone exists and must exit 0. `ready` is polled
  until it exits 0, for up to 180 seconds.
- For `lab shot`, the image needs `Xvfb`, `xdpyinfo`, and ImageMagick's `import` and
  `identify`.

## Bring a lab up

```
scripts/lab up demo --repo /path/to/repo --branch feat/demo --port 6551
```

`up` converges: it builds the image, recreates the container if the spec changed, checks the
branch out in the clone, runs `setup`, and waits for `ready`. A second run with no input change
prints `changed=0`. Progress goes to stderr, and one line to stdout:

```
lab name=demo container=lab-demo image=podman-sandbox/myrepo:latest work=/work/myrepo head=1a2b3c4d port=6551 changed=4
```

`--repo` defaults to the working directory's repository, and `--branch` to that repository's
current branch. `--port N` publishes port N on `127.0.0.1` and exports `LAB_PORT` into the
container. It is the only way to publish a port, and the second lab to claim a host port fails
to start, so give each lab its own.

## Run a command in a lab

```
scripts/lab exec demo pytest -q
scripts/lab exec demo bash -lc 'make 2>&1 | tail -40'
```

The working directory is the private clone, so you never write `cd`. Arguments after the lab
name pass through unparsed, and `exec` returns the command's own exit code.

## Screenshot a lab

```
scripts/lab shot demo --seconds 60 -- myapp --fullscreen
```

That runs a windowed command on a throwaway display and photographs it. Drop the `--` and
everything after it to photograph the display `setup` already started, leaving whatever runs on
it alone. `--seconds` defaults to 30. Both forms copy the PNG to the host and print one line:

```
shot path=/path/to/repo/.sandbox-shots/demo-2026-09-12T14-03-11Z.png size=1280x720 stddev=10497.7 colors=4093 bytes=223095
```

`--out PATH` names the file yourself. The default lands under `<repo>/.sandbox-shots/` with a
UTC timestamp.

Judge the frame from `stddev` and `colors`. Do not open the PNG, because its pixels then sit in
your context for the rest of the session. `shot` exits 1 when `colors` is 2 or fewer, and
`--allow-blank` turns that gate off.

## Tear a lab down

```
scripts/lab down demo
```

This deletes the container and its `lab-demo-work` volume. The clone and any uncommitted work in
it are gone, so save commits first. `podman ps -a --filter label=lab.spec` lists the labs that
exist.

## Save commits from a lab

If `lab up` refuses to reset a clone, it prints these three commands for each `REF` at risk,
with `NAME`, `REF`, and `SHA` filled in. Run them from the host repository.

```
scripts/lab exec NAME git bundle create /tmp/NAME.bundle REF
podman cp lab-NAME:/tmp/NAME.bundle /tmp/NAME.bundle
git fetch /tmp/NAME.bundle REF:refs/heads/lab-rescue/NAME-SHA
```

`SHA` is the first 12 characters of the newest commit at risk, so each rescue gets its own
`lab-rescue` branch. Then run `lab up` again, or `lab down NAME`.

## Check the host

```
scripts/lab check --repo /path/to/repo
```

`check` confirms podman answers, the repository's head resolves, and
`.sandbox-container/Containerfile` is there. It prints one `ok:` or `FAIL:` line per check,
exits 1 if any failed, and builds nothing.
