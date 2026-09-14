---
name: ox-security
description: Query OX Security as a connector aggregator for issues, apps, prioritization, and repo-to-runtime paths; use it for OX plus Snyk, Sysdig, Azure Repos, Azure Pipelines, ACR, and AKS questions via Issue.sourceTools and Application.applicationFlows, but never for Cloudflare WAF/CDN/DNS.
---

# ox-security

Paths below are relative to this skill's directory. Sends only allowlisted read-only `query` documents to OX's Apollo Gateway; cannot change anything in the vendor tenant.

Env: `OX_API_KEY` required. `OX_API_URL` optional. `OX_AUTH_BEARER=1` sends `Authorization: Bearer <key>` instead of the default bare key.

Rate limits: 1,000 req/hour, 15,000 req/day.

## Commands

Run `python3 ./ox_security.py <cmd> --help` for full flags (`issues --help` lists the 20 legal `--filter FIELD` keys).

| command | flags | returns |
|---|---|---|
| issues | --limit --severity --app --filter FIELD=VALUE --offset --cursorValue | issue prioritization: EPSS, percentile, exploit-in-the-wild, fix availability, source tool, app priority |
| apps | --search --limit --offset | app inventory: repo, branch, prod flag, priority, matched Snyk project |
| app-flows | appId | repo -> cicd -> artifact -> k8s -> cloud deployment flow for one app |

Route Snyk/Sysdig questions through `issues` (`Issue.sourceTools`). Route Azure Repos/Pipelines/ACR/AKS questions through `app-flows`.

## Example

```bash
python3 ./ox_security.py issues --limit 10 --severity Critical --app Org/repo
name	app	severity	tool_severity	tools	priority	epss	pct	wild	fix
Secret in code	api	Critical	High	Snyk	high	0.91	99	yes	yes
```

`severity` is OX's own severity (what `--severity` filters on); `tool_severity` is the source scanner's `originalToolSeverity`. The two can legitimately disagree.

## Gotchas

- Cannot answer Cloudflare WAF/CDN/DNS/Workers (not an OX connector, use the cloudflare skill), writes, comments, severity updates, exclusions, or arbitrary user-supplied GraphQL.
- `IssuesInput.search` and `GetApplicationsInput.filterSearch` validate but are silently ignored by this tenant (`--severity Critical` through `search` returns `totalFilteredIssues: 0` even though Critical issues exist). Do not revert `issues` filtering to `search`/`filterSearch`, that is the bug this tool works around. Use `--filter`/`--severity`/`--app` instead.
- `apps --search` (`GetApplicationsInput.search`, substring match) is the only working app filter; `filterSearch` is accepted and ignored.
- `--app` / `filters.apps` takes the fully qualified `Org/repo` app name, not the bare repo name.
- Paging is `--offset` + `--limit` only. `page` on both `IssuesInput` and `GetApplicationsInput` validates and is silently ignored (two different values return the same rows). `--cursorValue` is real and fails loudly if it does not match the sort used to obtain it.
- `Application.id` is deprecated, use `Application.appId`. `KubernetesItem` has no `cluster` or `region` field.
- `filters` (`IssueFilters`) is absent from OX's published SDL but is deployed and working; `fixedIssues` and `severity` are not valid filter keys and the server rejects them by name.
