---
name: cloudflare
description: Query Cloudflare accounts, zones, DNS exposure, rulesets, WAF managed ruleset posture, and Workers routes from the public Cloudflare API.
---

# cloudflare

Paths below are relative to this skill's directory. Read-only, GET only, cannot change anything in the vendor tenant.

Env: `CLOUDFLARE_API_TOKEN`.

## Commands

Run `python3 ./cloudflare.py <cmd> --help` for full flags.

| command | flags | returns |
|---|---|---|
| accounts | | visible accounts |
| zones | --account.name | zones in an account |
| dns | --zone [--proxied] | DNS records, `proxied` is the exposure flag |
| rulesets | --zone [--phase] | ruleset ids/name/kind/phase/version (no rules) |
| ruleset | --zone --id | one ruleset's rules |
| waf | --zone | managed WAF rulesets deployed at the zone entrypoint |
| routes | --zone | Workers routes |

## Example

```bash
python3 ./cloudflare.py dns --zone z1 --proxied false
name	type	content	proxied	ttl
origin.example.com	A	192.0.2.10	false	1
```

## Gotchas

- No writes, no cross-vendor correlation, no historical trending.
- No deprecated Firewall Rules/Filters API (unsupported since 2025-06-15; use Rulesets). No GraphQL analytics / `firewallEventsAdaptive` (POST endpoint, needs Account Analytics: Read, not in Cloudflare's OpenAPI).
- `rulesets` list omits rules by design; fetch `ruleset --zone ID --id RULESET_ID` for rules.
- `waf` reports OWASP Core Ruleset posture (paranoia level, score threshold) only for OWASP; other managed rulesets (Cloudflare Managed, Exposed Credentials) show `-` since those fields do not exist on them.
- A 404 on `ruleset`/`rulesets` for a phase means no custom deployment, not no protection: default managed rulesets can still be active. The tool exits 0 with `no entrypoint ruleset is deployed for this phase` on stdout (or `--raw` JSON `{"result":null,"no_entrypoint_ruleset":true,"phase":...}`).
- Common phases: `http_request_firewall_custom`, `http_request_firewall_managed`, `http_ratelimit`, `ddos_l7`, `ddos_l4`, `http_request_sbfm`.
- Rulesets use cursor pagination; the tool reads both `result_info.cursor` and `result_info.cursors.after`. DNS `--per-page` clamps to 5,000 (real-world cap, not the documented 5,000,000).
- Cloudflare rate limit: 1,200 calls/5min/user, 200/sec/IP. Tool self-throttles to a 0.25s call floor and honors `Retry-After` on 429.
- OWASP paranoia/threshold projection in `waf` is unverified live; needs a plan with OWASP Core Ruleset deployed.
