# Set up or change test runs

Goal: `mise run ci` gives the same result for a person and for CI. A new suite needs one new task and no other edit.

| The repository has | Go to |
|---|---|
| No `test:*` task | [Set up the test runs](#set-up-the-test-runs) |
| `test:*` tasks, and a suite to add | [Add a suite](#add-a-suite) |
| A suite to change or to remove | [Change or remove a suite](#change-or-remove-a-suite) |
| Two or more projects | [Monorepo](#monorepo) |

## Names

| Name | Rule |
|---|---|
| `test:<suite>` | One task for each suite, such as `test:unit`, `test:integration`, `test:e2e`. |
| `test` | An alias on `test:unit`. Do not make a task with the name `test`. `mise tasks validate` fails when a task and an alias have one name. |
| `ci` | `depends = ["lint:*", "test:*"]`. It has no `run`. |

Each pattern in `depends` must match a task. If the repository has no `lint:*` task, remove `"lint:*"`.

## Set up the test runs

1. **Find the suites.** Read the package scripts, the Makefile, the CI files, and the test config. Done when you can name each suite and its command.
2. **Get a baseline.** Run each command with `mise exec -- <command>`. Record each suite that fails before your change. Tell the user about each one.
3. **Add the tasks.** Use [templates/test-tasks.toml](../templates/test-tasks.toml) as the model. Add only the tasks that `mise.toml` does not have. Two tables with one name are a TOML error.
4. **Write each `run`.** Call the command that the repository has. If a suite has no command, put the test runner command in `run`.
5. **Decide the skip rule for each suite.** Use the [Skip](#skip) section.
6. **Wire CI.** Use the [CI](#ci) section.
7. **Verify.** Use the [Done](#done) section.

## Add a suite

1. Run `mise run --force ci`. If it fails, stop and tell the user.
2. Add one task. Change no other task. If the suite has no command in the repository, put the test runner command in `run`.

   ```toml
   [tasks."test:e2e"]
   description = "Run the end-to-end tests"
   run = "npx playwright test"
   ```

3. Decide the skip rule with the [Skip](#skip) section.
4. Make sure that the workflow agrees with the [CI](#ci) section.

Done when `mise tasks deps ci` lists the new task and `mise run --force ci` exits 0.

## Change or remove a suite

1. Run `mise run --force ci` before the change. If it fails, stop and tell the user.
2. Make the change. Run the suite, then run `mise run --force ci`.
3. If you remove the last `test:*` task or the last `lint:*` task, remove its pattern from `ci`.
4. If you remove `test:unit`, move the `test` alias to the suite that people run most.

## Arguments

- `mise run test:unit -- <arguments>` appends the arguments to the end of the `run` string.
- A package script needs its own separator. End the `run` with `--`, as in `npm test --`.
- `$@` is empty in a TOML `run`.
- To put an argument in a specific position, use the `usage` field or a file task. Start from [templates/file-task](../templates/file-task).

## Skip

A task with `sources` does not run again when its sources and its arguments are the same as in the last run.

- `mise run ci` can exit 0 with a suite skipped. To prove a setup, run `mise run --force ci`.
- Give `sources` only to a suite that reads only files in the repository.
- List each file that the suite reads: the tests, the code under test, the test config, and the dependency lockfile.
- Give no `sources` to a suite that reads external state, such as a database, a network service, or the clock.
- Do not set `outputs` on a test task. With `outputs = []`, mise does not skip the task.
- Make sure that each glob matches files. For a glob that matches no file, mise gives a warning, runs the task one time, and then skips it on each later run.

## Parallel runs

mise runs the dependencies of `ci` in parallel.

- If two suites share a port, a database, or a file, add `wait_for = ["test:<other suite>"]` to one of them.
- To run all tasks one at a time, use `mise run --jobs 1 ci`.

## Monorepo

1. Set up the monorepo config with [references/choosing-features.md](../references/choosing-features.md).
2. Give each project its own `test:<suite>` tasks and its own `ci` task, as in the Names table.
3. In the root `mise.toml`, add this task:

   ```toml
   [tasks.ci]
   description = "Run ci in every project"
   depends = ["//...:ci"]
   ```

A new project then runs under the root `ci` with no edit to the root config.
Run one project with `mise run //<path>:ci`. At the root, the root task has the name `//:ci`.

## CI

The workflow is correct when all of these are true:

- The job runs `mise run --force ci`. With `--force`, no suite skips.
- The job has no other lint or test command.
- The `env` of the job has `MISE_LOCKED: 1`. `mise install` then fails for a tool that the lockfile does not list.

If the repository has no workflow, run `mise generate github-action --write`. Without `--write`, the command only prints the workflow. Then edit the file until the three conditions are true. Check the rest of the file with the generator table in [references/choosing-features.md](../references/choosing-features.md).

## Do not use

Do not run `mise test-tool`. It tests registry tools, and it deletes installed tool versions. It does not run project tests.

## Done

The work is done when all of these are true:

- `mise tasks validate` exits 0.
- `mise tasks deps ci` lists each suite.
- `mise run --force ci` exits 0.
- The check script exits 0, as the Verify section of the skill says.
- The workflow agrees with the [CI](#ci) section.
