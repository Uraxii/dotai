---
name: azure-devops
description: Query Azure DevOps projects, repos, builds, pipelines, releases, environments, Kubernetes resources, and WIQL work item ids through read-only public REST APIs for CI, release, repository, and deployment inventory questions.
---

# azure-devops

Paths below are relative to this skill's directory. Thin read-only reader; `wiql` is the only POST (read-only WIQL, returns ids only).

Env: `AZURE_DEVOPS_ORG` plus `AZURE_DEVOPS_PAT` or `AZURE_DEVOPS_BEARER_TOKEN`. `--org` overrides org. `--api-version` overrides the per-endpoint default. Entra bearer alternative: `az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798` (CLI reads the token from env, does not shell out to `az`).

## Commands

Run `python3 ./azure_devops.py <cmd> --help` for full flags.

| command | required flags | returns |
|---|---|---|
| projects | | project list |
| repos | --project | git repos |
| items | --project --repoId | repo file/tree contents |
| pipelines | --project | pipeline definitions |
| runs | --project --pipelineId | pipeline runs (top 10000, no paging) |
| builds | --project | build list, filterable |
| artifacts | --project --buildId | build artifacts |
| deployments | --project | release deployments |
| releasedefs | --project | release definitions |
| release-env | --project --releaseId --environmentId | one release environment |
| environments | --project | YAML environments |
| k8s | --project --envId --resourceId | k8s resource for an environment |
| wiql | --project --query | work item ids only (no hydration) |

## Example

```bash
python3 ./azure_devops.py builds --project api
id	number	status	result	repo_id	repo_name	repo_type	repo_url	default_branch	source_version
7	20260101.1	completed	succeeded	r1	api	TfsGit	https://example	refs/heads/main	abc123
```

## Gotchas

- No writes, no pipeline preview dry runs (that endpoint queues a run), no cross-vendor correlation, no historical trending.
- `runs` LIST omits `resources` (only present on run-detail, not called), so repo refs/versions are unavailable there.
- Bare `7.2` api-version is undocumented; each endpoint needs its exact `-preview.N` suffix. `environments`, `k8s`, `release-env` default to `7.1-preview.N` (matching `azure-devops-python-api`) because the bare/`7.2` form 400s on these preview-only routes.
- Release Management lives on `vsrm.dev.azure.com`, not `dev.azure.com`.
- Azure DevOps OAuth deprecates fully in 2026; Entra is the recommended auth path.
- Read-only PAT scopes: `vso.project`, `vso.code`, `vso.build`, `vso.release`, `vso.serviceendpoint`, `vso.work`, `vso.profile`. `environments`/`k8s` additionally cost `vso.environment_manage`, a high-privilege scope with no read-only sibling.
- `x-ms-continuationtoken` response header is an undocumented real-world convention; read defensively.
