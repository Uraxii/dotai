# ASD-STE100 skill source

Imported from Dustin Yuchen Teng's `danyuchn/asd-ste100-skill` repository on 2026-11-18.

- Source: https://github.com/danyuchn/asd-ste100-skill/tree/707362731928d0d92526c066df15dbbe6a378c07
- Revision: `707362731928d0d92526c066df15dbbe6a378c07`
- License: MIT, retained in [LICENSE.md](LICENSE.md).

The skill, its references, examples, and linter are upstream's, unedited.
Upstream's README and plugin manifests are not vendored, because dotai
generates its own manifests.

dotai removes `examples/linter-edge-cases.md`: upstream's deliberately
non-STE test input for `scripts/ste-lint.py`. No skill file links it, so
it only failed the skill-quality orphan check.
