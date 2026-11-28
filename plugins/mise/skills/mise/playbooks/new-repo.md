# Set up mise in a repository

Goal: a person or a CI job clones the repository, runs `mise install` and `mise run ci`, and gets the same tools and the same result.

Do the steps in order. Do not start a step before the step above it is done.

1. **Find what the repository declares.**
   - Look for a mise config, `.tool-versions`, other version files, package scripts, a Makefile, and CI files.
   - If a mise config exists, read it. Then run `MISE_SAFE=1 mise ls --current` and `MISE_SAFE=1 mise tasks ls`.
   - Done when you can name each tool with its version, and each lint, test, and build command.

2. **Agree the scope.**
   - If another version manager is in use, give the user these options and wait for the answer:
     1. Keep it. Add only mise tasks.
     2. Keep its version files. Let mise read them.
     3. Move the versions to `mise.toml` and remove the old files.
   - If a tool has no version signal, ask the user for the version.
   - Done when each tool has an agreed version and an agreed source.

3. **Start the config.**
   - Copy [templates/mise.toml](../templates/mise.toml) to the repository root.
   - Set `min_version` to the version that `mise --version` prints.
   - For two or more projects in one repository, read the monorepo section of [references/choosing-features.md](../references/choosing-features.md).
   - Done when `mise.toml` is at the root.

4. **Add the tools.**
   - Choose the backend with [references/choosing-features.md](../references/choosing-features.md).
   - Run `mise use --pin <tool>@<version>` at the repository root for each tool. mise writes to the nearest config in a parent directory.
   - Remove the placeholder tool line.
   - Done when `mise ls --current` shows each tool as installed, with an exact version.

5. **Add the environment values.**
   - Choose the file for each value with [references/choosing-features.md](../references/choosing-features.md).
   - Add `mise.local.toml`, `mise.*.local.toml`, `mise.local.lock`, and `.env` to `.gitignore`.
   - Done when `git check-ignore mise.local.toml` exits 0, and no tracked file holds a secret value.

6. **Add the tasks.**
   - Replace each placeholder command with the command that the repository has.
   - Make one `lint:<tool>` task for each linter and one `test:<suite>` task for each suite. For the suites, follow [test-runs.md](test-runs.md).
   - If the repository has no linter, remove `lint`, `lint:code`, and `"lint:*"` from the `ci` task. A pattern that matches no task makes `mise run ci` fail.
   - Add a task for each other command that people run, such as the build. Give each task a `description`.
   - Done when `mise tasks validate` exits 0 and `mise run ci` exits 0.

7. **Make the lockfile.**
   - Run `mise lock`.
   - Done when `mise.lock` lists each tool.

8. **Wire CI.**
   - If the repository has a CI workflow, change its lint and test steps to one step that runs `mise run ci`. Do not add a second workflow.
   - If it has none, run `mise generate github-action`. Check the output with the generator table in [references/choosing-features.md](../references/choosing-features.md).
   - Set `MISE_LOCKED=1` in the CI job. `mise install` then fails for a tool that the lockfile does not list.
   - Done when the workflow has no lint or test command other than `mise run ci`.

9. **Tell people how to start.**
   - Put three commands in the README: `mise trust`, `mise install`, `mise run ci`.
   - Done when the README has them.

10. **Verify.**
    - Run the check script and `mise run ci`, as the Verify section of the skill says.
    - Commit `mise.toml`, `mise.lock`, `.gitignore`, the workflow, and the README.
    - Done when both commands exit 0 and `git status` shows no mise file that is not committed.
