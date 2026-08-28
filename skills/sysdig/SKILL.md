---
name: sysdig
description: Query Sysdig Secure read-only SaaS APIs for AKS runtime vulnerability posture, vulnerability result details, SBOM lookup, inventory, zones, and secure events.
---

# sysdig

Paths below are relative to this skill's directory. Read-only, GET only, cannot change anything in the vendor tenant.

Env: `SYSDIG_API_TOKEN` and `SYSDIG_HOST` (unless `--host` passed). Regions: `us1 us2 us3 us4 eu1 eu2 au1 me2 in1 jp1`.

## Commands

Run `python3 ./sysdig.py <cmd> --help` for full flags.

| command | flags | returns |
|---|---|---|
| runtime | --running --filter | runtime vulnerability results, running vs total vuln counts, cluster/namespace |
| registry | --filter | registry scan results |
| pipeline | --filter | pipeline scan results |
| result | --id | one result's per-vulnerability detail: exploitable, exploit, accepted risks, fixed_in |
| sboms | | SBOM lookup (v1beta1 only, no v1 path exists) |
| inventory | --filter | resource inventory |
| zones | --filter | zones (`filter=name:<value>` only) |
| events | | secure events |

## Example

```bash
python3 ./sysdig.py --host us2 runtime --running
id	asset	type	cluster	namespace	running_vulns	total_vulns	policy
r1	ghcr.io/acme/api:1.2	containerImage	prod	orders	critical:2,high:4,medium:0,low:0,negligible:0	critical:10,high:22,medium:5,low:0,negligible:0	failed
```

## Gotchas

- Covers AKS runtime only. No Azure App Service, Azure Functions, or Cloudflare Workers signal, route those elsewhere.
- No risk/attack-path data: served by internal `/api/scanning/riskmanager/v2/definitions` and `/api/graph/v1/graphql`, not called here. No Reporting v2, SysQL, writes, cross-vendor correlation, or historical trending.
- No published rate-limit quotas; VM endpoints emit `x-ratelimit-limit`/`x-ratelimit-remaining`/`x-ratelimit-reset` headers.
- Host by path family: `/secure/...` uses `api.<region>.sysdig.com`. `/api/...` and `/platform/...` use the app host: `us2`/`eu1` -> `<region>.app.sysdig.com`; `us3 us4 eu2 au1 me2 in1 jp1` -> `app.<region>.sysdig.com`; `us1` -> `secure.sysdig.com`.
- `runtime`/`registry`/`pipeline`/`result` use `/secure/vulnerability/v1/...`. The `v1beta1` forms of those four paths were deprecated 2025-02-25 (migrate-by 2025-09-01) and are replaced one-for-one, except `sboms` and `accepted-risks`, which stay on `v1beta1` since no `v1` path exists for them.
- `v1` renamed `mainAssetName` to `pullString` on registry/pipeline results; `runtime` keeps `mainAssetName` and gained `resourceId`. `_basic_rows` falls back `mainAssetName` -> `pullString` -> `name`.
- Unrelated: the legacy V1 scanning engine (`/api/scanning/v1/anchore`) reached end of life 2024-12-31, do not confuse with the v1beta1 vulnerability deprecation above.
- Pagination is endpoint-specific: vulnerability lists and events use opaque cursor pagination from `page.next` resent as `cursor`; inventory uses `filter`/`withEnrichedContainers`/`pageSize`/`pageNumber` with `page.next` as next page number and `page.total` as page count; `zones` has no `/api` prefix and returns a `zones` wrapper.
- `GET /secure/vulnerability/v1beta1/accepted-risks` exists but is absent from the source spec (IBM's republication of the Sysdig Workload Protection OpenAPI), so it is not implemented; response shape unverified.
