# Text with quotes or several lines

The shell runs backticks and `$(...)` inside double quotes.
A quote in the text can end the string early.
Put text in a file when it has several lines, a quote, a backtick, or `$(...)`.
Write the file with a quoted heredoc, `<<'EOF'`, or your harness's file tool.
Pass the file to the command.

| Text | Command |
| --- | --- |
| PR body | `gh pr create --body-file <file>` or `gh pr edit --body-file <file>` |
| Close reason | `bd close <id> --reason-file <file>` |
| Comment | `bd comment <id> --file <file>` |
| Description | `bd update <id> --body-file <file>` |

Use `-` in place of `<file>` to read text from stdin. `bd comment` also takes `--stdin`.
Short text with no quote, backtick, or `$` can stay inline.
