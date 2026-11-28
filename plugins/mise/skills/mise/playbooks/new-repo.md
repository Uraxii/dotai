# Set up mise in a repository

Goal: a person or a CI job clones the repository, runs `mise install` and `mise run --force ci`, and gets the same tools and the same result.

Do the steps in order. Do not start a step before the step above it is done.

1. **Find what the repository declares.**
   - Look for a mise config, `.tool-versions`, other version files, package scripts, a Makefile, and CI files.
   - If a mise config exists, read it. Then run `MISE_SAFE=1 mise ls --current` and `MISE_SAFE=1 mise tasks ls`.
   - Done when you can name each tool with its version, and each lint, test, and build command.

2. **Agree the scope.**
   - If another version manager is in use, give the user these options and wait for the answer:
     1. Keep it. Add only mise tasks.
     2. Keep its version files. Let mise read them. This option is not possible for `.tool-versions`. See the version source table in [references/choosing-features.md](../references/choosing-features.md).
     3. Move the versions to `mise.toml` and remove the old files.
   - If a tool has no version signal, ask the user for the version.
   - Done when each tool has an agreed version and an agreed source.

3. **Start the config.**
   - If the repository has no `mise.toml`, copy [templates/mise.toml](../templates/mise.toml) to the repository root.
   - If it has one, do not copy over it. Add the parts that it does not have, with the template as the model.
   - Remove the placeholder tool line. `mise use` fails while that line is there.
   - Set `min_version` to the version that `mise --version` prints.
   - Run `mise trust` at the repository root. Without it, `mise use` stops with a `not trusted` error.
   - For two or more projects in one repository, read the monorepo section of [references/choosing-features.md](../references/choosing-features.md).
   - Done when `mise config ls` exits 0.

4. **Add the tools.**
   - Choose the backend with [references/choosing-features.md](../references/choosing-features.md).
   - Run `mise use --pin <tool>@<version>` at the repository root for each tool. mise writes to the nearest config in a parent directory.
   - If the user chose to move the versions, remove the old version files now.
   - Done when `mise ls --current` lists each tool with an exact version and shows no tool as missing.

5. **Add the environment values.**
   - Choose the file for each value with [references/choosing-features.md](../references/choosing-features.md).
   - Add `mise.local.toml`, `mise.*.local.toml`, `mise.local.lock`, and `.env` to `.gitignore`.
   - Done when `git check-ignore mise.local.toml` exits 0, and no tracked file holds a secret value.

6. **Add the tasks.**
   - Replace each placeholder command with the command that the repository has. Delete the template comment above it.
   - Give each lint task the name of its linter, such as `lint:eslint`. Rename `lint:code`.
   - Make one `test:<suite>` task for each suite. Follow [test-runs.md](test-runs.md).
   - If the repository has no linter, remove `lint`, `lint:code`, and `"lint:*"` from the `ci` task. A pattern that matches no task makes `mise run ci` fail.
   - Add a task for each other command that people run, such as the build. Give each task a `description`.
   - Done when `mise tasks validate` exits 0 and `mise run --force ci` exits 0.

7. **Make the lockfile.**
   - Run `mise lock`.
   - Done when `MISE_LOCKED=1 mise install --dry-run-code` exits 0.

8. **Wire CI.**
   - Follow the CI section of [test-runs.md](test-runs.md).
   - Done when that section's conditions are true.

9. **Tell people how to start.**
   - Put three commands in the README: `mise trust`, `mise install`, `mise run ci`.
   - Done when the README has them.

10. **Verify.**
    - Run the check script and `mise run --force ci`, as the Verify section of the skill says.
    - Done when both commands exit 0.
