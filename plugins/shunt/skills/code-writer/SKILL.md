---
name: code-writer
description: "Delegate boilerplate code generation to AiKA. Use for tests, config, docstrings, type stubs, or any generation where >80% is predictable from reference files."
compatibility: Needs access to Portal AiKA.
license: Apache-2.0
metadata:
  version: 1.0.0
  author: Spotify
  homepage: https://github.com/Uraxii/dotai
  source: https://github.com/spotify/portal-ai-plugins/tree/e14bdb1dc894e0a2ef150fa811db5308ae2ddb37/plugins/shunt
---

Run the script from this plugin's `scripts/` directory, two levels above this skill's base directory.

```bash
# Generate and write directly to target file
"<skill base directory>/../../scripts/code-write" --spec "<what to generate>" --reference <reference-file> --target <output-path>

# Output to stdout instead (omit --target)
"<skill base directory>/../../scripts/code-write" --spec "<what to generate>" --reference <reference-file>
```

Each call is independent. To build on what was just generated, pass that file as the
`--reference` for the next call.

Review the output and make surgical edits for the ~5-20% that needs Claude-level judgment.
