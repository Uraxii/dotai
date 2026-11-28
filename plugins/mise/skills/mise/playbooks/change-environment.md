# Change a mise environment

Two rules apply to each procedure in this file.

- **Before the change**, run `mise run ci`. If it fails, stop and tell the user. Do not mix an old failure with your change.
- **After the change**, run the check script and `mise run ci`, as the Verify section of the skill says. Commit `mise.toml` and `mise.lock` together.

## Add a tool

1. Choose the backend with [references/choosing-features.md](../references/choosing-features.md).
2. Run `mise use --pin <tool>@<version>` at the repository root.
3. Run `mise lock`.

Done when `mise exec -- <tool> --version` prints the pinned version, and `mise.lock` lists the tool.

## Upgrade a tool

Upgrade one tool at a time.

1. Find the new version with `mise outdated` or `mise latest <tool>@<version line>`.
2. Run `mise use --pin <tool>@<new version>`.
3. Run `mise lock`.
4. Run `mise run ci`. If it fails, repair the cause or put the old version back.
5. Search the repository for the old version. Update each file that states it, such as a CI file, a container file, a version file, or the documentation.

Done when `mise run ci` exits 0 and the search finds no old version.

## Remove a tool

1. Search the tasks and scripts for commands that use the tool. Remove or replace them.
2. Run `mise use --remove <tool>`.
3. Run `mise lock`. Then read `mise.lock`. If it still lists the tool, remove that entry.

Done when `mise ls --current` does not show the tool and `mise run ci` exits 0.

## Add an environment value

1. Choose the file with the environment table in [references/choosing-features.md](../references/choosing-features.md).
2. For a value that is not secret, run `mise set <NAME>=<value>`.
3. For a secret value, add `<NAME> = { required = "<how to get it>" }` to `[env]`. Tell the user to put the value in `mise.local.toml`. Do not handle the value yourself.

Done when `mise exec -- sh -c 'test -n "$<NAME>"'` exits 0. This command does not print the value.

## Add or change a task

1. Choose the task form with the task table in [references/choosing-features.md](../references/choosing-features.md).
2. Use a name from the Task names table of the skill. For a test task, follow [test-runs.md](test-runs.md).
3. Add the task with `mise tasks add`, or edit `mise.toml`. Give the task a `description`.
4. Run `mise tasks validate`. Then run the task.

Done when `mise tasks validate` exits 0 and `mise run <task>` exits 0.

## Raise `min_version`

Raise it when the config uses a feature that an older mise does not have.

1. Set `min_version` to the version that `mise --version` prints.
2. Update the mise version that CI installs, if CI pins one.

Done when `mise run ci` exits 0 on your machine and in CI.
