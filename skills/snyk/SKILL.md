---
name: snyk
description: Query Snyk REST API orgs, token identity, projects, targets, issues, issue details, and Early Access findings for read-only inventory and vulnerability prioritization.
---

# snyk

Paths below are relative to this skill's directory. Read-only, GET only, cannot change anything in the vendor tenant. Most Snyk REST endpoints are Enterprise-plan only; Free/Team personal tokens cannot use this API at all (IDE/CLI/CI use only).

Env: `SNYK_TOKEN` required. `SNYK_API_HOST` optional, defaults `api.snyk.io`; region hosts `api.us.snyk.io`, `api.eu.snyk.io`, `api.au.snyk.io` (tokens are region-bound).

Default API version `2026-03-25`, override with `--version`. Rate limit 1620 calls/min/key. `--org`/`--group`/`--group-id`/`--target-id` must be UUIDs, not slugs (rejected locally); resolve a slug first with `orgs --slug <slug>`.

## Commands

Run `python3 ./snyk.py <cmd> --help` for full flags.

| command | flags | returns |
|---|---|---|
| orgs | --slug --group-id | orgs visible to this token |
| self | | token identity |
| projects | --org --target-id ... | projects in an org |
| targets | --org --limit ... | targets in an org |
| issues | --org --severity --status ... | org/group issues: risk score, `risk.factors[]`, reachability, fixability |
| issue | --org --id | one issue's detail |
| findings | --org --test | EPSS for one test id (only Snyk REST source for EPSS) |

## Example

```bash
python3 ./snyk.py issues --org $ORG_ID --severity high --severity critical
id	severity	status	type	problem	risk	risk_model	factors	reachability	fixable	scan_item_id
i1	high	open	package_vulnerability	CVE-2026-0001	891	riskScore	deployed,loaded_package	function	true	p1
```

## Gotchas

- No writes, no cross-vendor correlation, no historical trending, no KEV field (only signal is the literal string `CISA` inside `exploit_details.sources[]`, visible with `--raw`).
- No EPSS from `issues`; use `findings` for EPSS.
- `findings --test` needs a `test_id`, obtainable only by POSTing `/orgs/{org_id}/tests`. This tool never does that POST, so `--test` must come from a `snyk` CLI run or a prior POST done elsewhere.
- `risk`/`risk_model` come from `attributes.risk.score.{value,model}`; GA can carry either the legacy priority score or the newer Risk Score, distinguished by `risk_model`. `factors`/`reachability` print `n/a` when the field is absent (unentitled tenant) and `-` only when present but empty (entitled, nothing found).
- Multiple `--severity`/`--status` send as one comma-joined param; `--target-id` on `projects` repeats instead (`target_id=a&target_id=b`), per the spec.
- `targets` server default for `exclude_empty` is `true` (silently drops targets with zero projects); this tool always sends `exclude_empty=false` unless `--exclude-empty` overrides it.
- Limit bounds: `orgs`/`projects`/`issues` are 10-100 and a multiple of 10; `targets`/`findings` are 1-100, no step. Out-of-range or wrong-step `--limit` is rejected locally, never silently rounded.
- Pagination: pass the exact `next:` value verbatim to `--next`. It is a relative path (no `/rest` prefix) already carrying `version` and `starting_after`; no scope flags are needed alongside `--next`, the tool fetches it verbatim and skips scope validation. `links.next` may arrive as `{"href":...,"meta":{...}}` instead of a bare string; the tool unwraps `href` either way.
- Auth header is `Authorization: token <TOKEN>`; `Accept`/`Content-Type` are `application/vnd.api+json`. The bare `https://api.snyk.io/rest/openapi` URL (no version segment) returns only version strings, not schemas, do not cite it as a source.
- `findings` is `x-snyk-api-stability: beta`, no `~experimental`-suffixed version exists for it after 2024-10-15.
- Unverified against a live tenant: whether unknown params 400 or are ignored, whether comma-joined filters need literal commas vs `%2C`, default `status`/`ignored` behavior when unset, whether `links.next` ever arrives in object form in production, and whether an under-permissioned token 403s cleanly or returns 200 with empty `data[]`.
