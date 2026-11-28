# Choosing mise features

Names in this file change between mise releases. Run the query that each section gives before you rely on a name.

## Tool backend

1. Run `mise registry <tool>`. If the registry has the tool, use the short name. The registry lists the preferred backend first.
2. If the registry does not have the tool, use the first backend in this order that can install it:
   1. `packslip:` when the vendor publishes a signed manifest.
   2. `aqua:`.
   3. `github:`, `gitlab:`, or `forgejo:` for a release binary.
   4. A language package backend: `npm:`, `pypi:`, `cargo:`, `go:`, `gem:`.
   5. A plugin backend, `vfox:` then `asdf:`.
3. Run `mise tool <tool>` and read its security line. Prefer a backend that verifies a checksum or an attestation.
4. Do not use a backend that mise reports as deprecated.

Query: `mise backends ls`, `mise search <name>`, `mise install --dry-run <backend>:<tool>`.

## Version source

| The repository has | Do this |
|---|---|
| No version file | Put exact versions in `mise.toml`. |
| `.tool-versions` | mise reads it. Keep it if another tool reads it. If not, move the versions to `mise.toml`. |
| `.nvmrc`, `.python-version`, or a similar file | mise does not read it by default. If CI or another tool reads the file, keep it and add the tool to the `idiomatic_version_file_enable_tools` setting. If not, move the version to `mise.toml`. |

`mise.toml` wins over `.tool-versions` in the same directory.
`mise use --pin <tool>@<version>` writes the exact version. Without `--pin`, mise writes the request as typed, such as `24` or `latest`.

Query: `mise settings ls --all`, `mise ls --current`.

## Task form

| Need | Use |
|---|---|
| One command or a short chain | A TOML task in `mise.toml`. |
| Shell logic, or typed arguments | A file task. Start from [templates/file-task](../templates/file-task). |
| The repository has the command as a package script or a Makefile target | A TOML task that calls it. Do not copy its body. |
| Many tasks with one shape | `[task_templates.<name>]`, then `extends = "<name>"` in each task. |

- mise appends extra arguments to the end of the `run` string. `$@` is empty in a TOML `run`.
- To put an argument in a specific position, or to give it a type, use the `usage` field.
- `task_config.includes` replaces the default task directories. List each directory that you want.
- A file task must be executable. mise ignores a file that is not.

Query: `mise tasks ls`, `mise tasks info <task>`, `mise tasks validate`.

## Environment value

| The value | Put it in |
|---|---|
| Is not secret and is the same for everyone | `[env]` in `mise.toml`. |
| Changes with the environment, such as staging or CI | `mise.<env>.toml`. Select it with `MISE_ENV` or `-E`. |
| Is for one machine, or is secret | `mise.local.toml`. Keep this file out of git. The user adds a secret value, not the agent. |
| Is in an env file that the repository has | `_.file = ".env"` in `[env]`. Keep the env file out of git. |
| Must exist and has no safe default | `NAME = { required = "<how to get it>" }`. `mise run` then stops with that help text. |
| Comes from a secret manager | Ask the user. The secret sources in mise are experimental. |

`mise.local.toml` wins over `mise.<env>.toml`, and that wins over `mise.toml`.
`mise set NAME=value` writes to `mise.toml` unless you give `--file`.

Query: `mise config ls` shows the files that mise loads, in order.

## One config or a monorepo

- One project: use one `mise.toml` at the root.
- Two or more projects with their own tools or tasks: set `monorepo_root = true` and `[monorepo] config_roots = [...]` in the root `mise.toml`. Give each project its own `mise.toml`.
- A monorepo task has the name `//<path>:<task>`. `//...:<task>` selects that task in each project.
- In a project directory, a root task needs the name `//:<task>`.

Query: `mise tasks ls --all`.

## Generators

| Need | Command | Check in the output |
|---|---|---|
| CI workflow | `mise generate github-action` | The push trigger uses the current branch name. The action references are tags. Pin them if the repository pins actions. |
| Task documentation | `mise generate task-docs` | Nothing. |
| Devcontainer | `mise generate devcontainer` | The base image. |
| Script that installs a pinned mise | `mise generate install-script` | The mise version in the script. |

Do not use `mise generate config` for a new repository. It writes only comments. Start from [templates/mise.toml](../templates/mise.toml).

Query: `mise generate --help`.

## Experimental features

A feature is experimental when one of these is true:
- `mise --help` or `mise <command> --help` shows `[experimental]` next to it.
- mise answers `... is experimental. Enable it with` and names the `experimental` setting.

Do not set `experimental = true` on your own decision. Tell the user which feature needs it and why. The user decides.
