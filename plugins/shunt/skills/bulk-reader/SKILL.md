---
name: bulk-reader
description: "Delegate bulk file reading to AiKA. Use when you need to read files >350 lines, answer questions across 3+ files, or summarize large diffs."
---

Run the script from this plugin's `scripts/` directory, two levels above this skill's base directory.

```bash
"<skill base directory>/../../scripts/bulk-read" --question "<question>" --paths <file1> [<file2> ...]
```

Each call is independent. To ask a follow-up, ask again with the same `--paths` — the files
go to AiKA, never into your context, so re-sending them costs you nothing.

Verify specific line numbers or exact values before using them in edits.
