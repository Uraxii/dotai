# GitHub CLI (`gh`)

Requires authenticated `gh` 2.99 or later.

## Inspect the Change

```bash
git branch --show-current
git status --porcelain
gh pr view --json number,title,body,url,baseRefName,headRefName
gh repo view --json defaultBranchRef
```

If `gh pr view` reports that no PR exists, continue with first-time PR
creation. For an existing PR, use its `baseRefName`; otherwise use the
`defaultBranchRef` of the repository.

## Attach Media

Attach media with `--attach` and reference it as `![alt](./file.webp)`; `gh`
replaces the path with the uploaded URL.

## Create or Update

Write the body to a temporary Markdown file, then create the PR as a draft:

```bash
gh pr create --draft --title '<title>' --body-file /tmp/pr-body.md --attach ./after.webp
```

When the PR is ready for the user to view, convert it from a draft:

```bash
gh pr ready PR_NUMBER
```

Update existing PRs:

```bash
gh pr edit PR_NUMBER --title '<title>' --body-file /tmp/pr-body.md --attach ./after.webp
```

Read the PR status:

```bash
gh pr view PR_NUMBER
```
