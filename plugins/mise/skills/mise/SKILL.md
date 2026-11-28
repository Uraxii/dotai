---
name: mise
description: Sets up and changes mise (mise-en-place) in a repository, covering tool versions, environment values, tasks, the lockfile, test runs, and CI. Use when a repository needs a new mise.toml, when a tool, an environment value, or a task is added, upgraded, or removed, when test suites or the ci task are set up or changed, or when a choice is needed between mise backends, version files, task forms, or config files. Gives playbooks, templates, a chooser, and a script that checks the setup. Covers mise.toml, mise.lock, tool versions, task runner, dev environment, test tasks, and monorepo tasks.
compatibility: Needs mise and bash.
metadata:
  version: 1.0.0
  author: Uraxii
  homepage: https://github.com/Uraxii/dotai
---

# mise

## Ground rules

1. Run a tool with `mise exec -- <command>`. Run a task with `mise run <task>`. An agent shell has no mise activation, so a bare command runs the system tool.
2. Do not rely on shims. A shim can run a system binary of the same name and give no error.
3. Run `mise <command> --help` before you use a flag or a subcommand. The mise documentation describes the newest release. `mise run` reads an unknown flag as a task name.
4. Pin each tool to an exact version with `mise use --pin`. Keep `mise.toml` and `mise.lock` in one commit.
5. Wrap the test, lint, and build commands that the repository has. Do not replace them.

## Trust and secrets

- Read each mise config file in a repository that you did not set up, before you run a mise command there. `mise run`, `mise exec`, and `mise install` trust the config with no prompt and install each missing tool.
- Other mise commands can stop with a `not trusted` error. Run `mise trust` after you read the config.
- To inspect a config without trust, set `MISE_SAFE=1`. mise then loads tools and tasks and drops `[env]`.
- A secret value is a password, a token, a key, or a URL that holds one.
- Put no secret value in a file that git tracks. The user adds a secret value, not the agent.
- Do not print the output of `mise env` into a reply or a log. Do not copy the `mise://env` MCP resource. mise hides a secret value only in task output.
- Do not turn on an experimental feature on your own decision. The user decides.

## Which file to read

| The work | Read |
|---|---|
| The repository has no mise config, or has one that is not complete | [playbooks/new-repo.md](playbooks/new-repo.md) |
| Add, upgrade, or remove a tool. Add an environment value. Add or change a task | [playbooks/change-environment.md](playbooks/change-environment.md) |
| Set up, add, change, or remove a test suite. Wire the `ci` task or CI | [playbooks/test-runs.md](playbooks/test-runs.md) |
| Choose a backend, a version file, a task form, an environment file, a monorepo layout, or a generator. Find out if a feature is experimental | [references/choosing-features.md](references/choosing-features.md) |

## Task names

| Name | What it is |
|---|---|
| `lint:<tool>` | One task for each linter. |
| `test:<suite>` | One task for each test suite. |
| `test` | An alias of `test:unit`. |
| `lint` | Runs each `lint:*` task. |
| `ci` | Depends on `lint:*` and `test:*`. People run `mise run ci`. CI runs `mise run --force ci`. |

To add a linter or a suite, add one task. No other task changes.

## Templates

- [templates/mise.toml](templates/mise.toml) is the base config for a repository that has none.
- [templates/test-tasks.toml](templates/test-tasks.toml) is the test block for a repository that has a `mise.toml`.
- [templates/file-task](templates/file-task) is a script task with typed arguments. Copy it to `mise-tasks/<task name>` and make the file executable.

Each placeholder starts with `REPLACE_WITH_`. Replace each one, and delete the template comment above it. The check script fails while a placeholder remains.

## Verify

1. Run `scripts/check-mise-setup.sh -C <repository>`. Each `FAIL` line has a `fix:` line below it. Do the fix and run the script again.
2. Run `mise run --force ci` in the repository. Without `--force`, mise can skip a suite and exit 0.

The work is done when both commands exit 0.

- The script only reads. It does not trust a config, install a tool, or run a task. Its last line gives the number of failures.
- In a monorepo, run the script for the root and for each project.
- Do not use `mise doctor` as the check. It fails in each shell that has no mise activation.

## Ask the user

Stop and ask when one of these is true:

- The repository gives no signal for the version of a tool.
- Another version manager is in use, and the request does not say to keep it or to replace it.
- A feature needs the `experimental` setting.
- A task needs a secret value.
