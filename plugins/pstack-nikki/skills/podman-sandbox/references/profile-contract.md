# The podman-sandbox profile contract

A profile is the environment a lab runs. It is a directory on your disk, not
code inside this skill. Adding one never means editing a file the skill
ships.

## What a profile directory holds

| File | Required | Purpose |
| --- | --- | --- |
| `Containerfile` | Yes | The image recipe. podman builds the directory as its context. |
| `profile.json` | No | Declares a published port and two lifecycle hooks. |
| Anything else | No | Reaches the build context, so a `COPY` in the Containerfile can use it. |

A directory holding only a `Containerfile` is a complete profile.

## Where the tool looks

`lab` searches these directories in order and takes the first match:

1. `<repo>/.nikki-agents/podman-sandbox/profiles/<name>/`
2. `~/.config/podman-sandbox/profiles/<name>/`
3. `<this skill>/profiles/<name>/`

Put a profile in the repo when it belongs to one project. Put it in
`~/.config/podman-sandbox/profiles/` when you want it in every project. The
skill ships one profile, `base`, in the third directory.

## profile.json

Every key is optional. An absent file means every default applies.

```json
{
	"port": 6551,
	"setup": ["/usr/local/bin/my-setup"],
	"ready": ["/usr/local/bin/my-ready"],
	"ready_timeout_sec": 180
}
```

`port` (integer, default none)
: The port the container listens on. `lab up` publishes it as
  `127.0.0.1:<port>:<port>`, so nothing on the local network reaches it, and
  exports it into the container as `LAB_PORT`. Read `LAB_PORT` in your hooks
  rather than hardcoding the number, because `lab up --port N` overrides this
  value. Two labs cannot publish the same host port: give the second one
  `--port`.

`setup` (list of strings, default none)
: An argument list run inside the container after the private clone exists,
  with the clone as its working directory. Use it for work that needs the
  clone and so cannot happen at build time: copying an addon in, writing a
  config value, running an import pass, starting a long-running process on
  the persistent display `:99`. It must exit 0. `lab up` skips it when the
  lab keeps running and the profile stays unchanged. It runs setup again after
  the container starts, including a restart, or when the profile changes.

`ready` (list of strings, default none)
: An argument list polled inside the container until it exits 0. Use it to
  prove the thing `setup` started is actually answering. Without it, `lab up`
  returns as soon as the clone is in place.

`ready_timeout_sec` (integer, default 180)
: How long `ready` may take before `lab up` fails and names the lab. Software
  rendering is slow; a first launch on llvmpipe can take a minute.

`setup` and `ready` are argument lists, never shell strings. `lab` passes each
element to podman as one argument. To run a pipeline, write a script, `COPY`
it into the image, and name the script.

## Rules a profile must follow

- **Build from `podman-sandbox/base:latest` if you want screenshots.** `base`
  installs Xvfb and ImageMagick and provides `/usr/local/bin/lab-shot`. A
  profile that starts `FROM debian:13-slim` instead is valid, and `lab shot`
  against it fails.
- **Fetch your tools from upstream inside the Containerfile.** A `COPY` from
  a path on the author's machine makes the profile work on that machine only.
- **Keep `/work` writable and leave `/src-ro` alone.** `lab` mounts the real
  repository read-only at `/src-ro` and the private clone's volume at
  `/work`. A `VOLUME` or `WORKDIR` of your own under either path fights the
  tool.
- **Make `setup` idempotent.** It runs after each container start or profile
  edit. It must not fail on a clone it already prepared.

## A minimal profile, end to end

Add Node to a lab. The whole profile is one file:

```
mkdir -p .nikki-agents/podman-sandbox/profiles/node/
```

`.nikki-agents/podman-sandbox/profiles/node/Containerfile`:

```
FROM podman-sandbox/base:latest
RUN apt-get update -qq \
	&& apt-get install -y -qq --no-install-recommends nodejs npm \
	&& rm -rf /var/lib/apt/lists/*
```

Then:

```
lab up nodetest --profile node
lab exec nodetest node --version
```

## Test your profile

Run these four in order. Each one fails on a different mistake.

1. `lab check --profile <name>` finds the directory, finds the
   Containerfile, and parses `profile.json`. It builds nothing, so it is
   fast and it is the first thing to run after an edit.
2. `lab up <labname> --profile <name>` builds the image, runs `setup`, and
   waits for `ready`. A build error, a failing setup, or a ready timeout
   shows here with the log path.
3. `lab up <labname> --profile <name>` a second time prints `changed=0`.
   Anything else means something in the converge path is not idempotent.
4. `lab exec <labname> <your tool> --version` proves the tool is on `PATH`
   in the image, not only in the build log.

For a profile that starts a process, add `lab shot <labname>` and read the
`stddev` and `colors` numbers it prints. A `colors=2` or lower exit 1 means
nothing rendered on the display.

## What the previous version required, and no longer does

Adding a profile used to mean dropping a `Containerfile.<name>` inside the
skill's own `scripts/` directory and adding a case to a `tool_binary_for`
shell function in the skill's own code. Both are gone. A profile is a
directory, and the skill holds no per-profile code.
