## Conventional Commits & Branches

This repo uses release-please to cut tags (including per-package tags like `cli-v*`) by parsing Conventional Commits on `main`. Squash-merges collapse a PR into a single commit whose subject is the PR title, so the PR title MUST also be a valid Conventional Commit — otherwise release-please skips the path and no release is cut.

### Commit messages

Use the Conventional Commits format for every commit:

```text
<type>(<scope>): <subject>
```

- **type** (required): `feat`, `fix`, `perf`, `docs`, `refactor`, `test`, `build`, `ci`, `chore`
- **scope** (recommended): the package or area touched. For release-please to attribute a commit to a sub-package, use the matching scope:
  - `packages/cli/**` → `(cli)`
  - `loovie-mcp/**` → `(mcp)`
  - root-level changes → omit scope or use the affected area (`(ci)`, `(docs)`, `(workflows)`, etc.)
- **subject**: imperative, lowercase, no trailing period. No em-dashes; commas/colons/dots only.

Breaking changes: append `!` after the type/scope (`feat(cli)!: …`) or include a `BREAKING CHANGE:` footer.

### PR titles

PR titles MUST follow the same Conventional Commits format, because squash-merge uses the PR title as the commit subject on `main`. Examples:

- Good: `feat(cli): add doctor command for client wiring checks`
- Good: `fix(mcp): correct manifest path for DXT bundle`
- Bad: `Feat/mcp distribution` (branch name, not a conventional commit — release-please will skip it)
- Bad: `Update CLI` (no type, no scope)

### Branch names

Use the pattern `<type>/<short-kebab-description>`:

- `feat/cli-doctor-command`
- `fix/mcp-manifest-path`
- `chore/bump-cosign`

Branch names are not parsed by release-please, but keep them aligned with the intended PR type so the eventual PR title is obvious.

### Before opening / merging a PR

- Confirm the PR title parses as a Conventional Commit with the right scope for the package being touched.
- If a PR touches multiple packages that need independent release tracking, prefer splitting into separate PRs so each can carry an accurate scope.
- Never merge a PR whose title would land a non-conventional squash commit on `main`.
