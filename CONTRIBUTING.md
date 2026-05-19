# Contributing to Loovie Community

Thanks for your interest. This repo is the open contract and reference servers for the Loovie BYO ("Bring Your Own") generation protocol. Contributions of any size are welcome, from typo fixes to new workflows to alternative server implementations.

## Status: community-supported beta, no SLA

This is a free public beta. We watch issues and PRs as best we can, but we do not commit to response times or fixes during beta. The fastest way to get help is the Loovie Discord (link in README once the server opens). Use GitHub Issues for reproducible bugs and discrete feature requests.

## What lives where

```
openapi/                 # The HTTP contract any BYO server implements (normative).
comfyui-loovie/          # Reference ComfyUI implementation (Python).
examples/minimal-server/ # Framework-agnostic FastAPI reference (Python).
docker/                  # Dockerfile + RunPod template + model downloader.
docs/                    # Long-form setup, security, troubleshooting guides.
.github/                 # Issue and PR templates, workflows, Dependabot.
```

## The contract is the line

The single most important rule: **the OpenAPI spec at `openapi/loovie-server.openapi.yaml` is the source of truth.** Any change that affects what a server returns or accepts must update the spec, and any change to the spec must be reflected in the reference implementations and tests. CI enforces this via lint and contract tests.

If you're implementing the protocol in a stack other than ComfyUI (Diffusers, SD-Next, your own server) — the contract is what you target. Open a PR in `examples/` if you want to ship a reference for your stack alongside ours.

## Sign-off (DCO), not a CLA

Every commit must be signed off under the [Developer Certificate of Origin](https://developercertificate.org/) by adding a `Signed-off-by` line. Configure git once:

```sh
git config user.name "Your Real Name"
git config user.email "you@example.com"
```

Then sign every commit:

```sh
git commit -s -m "feat(comfyui-loovie): add LoRA stacking support"
```

This adds `Signed-off-by: Your Real Name <you@example.com>` to the commit message. By signing off, you certify the [DCO 1.1](https://developercertificate.org/) for that contribution:

```
Developer Certificate of Origin
Version 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.
```

We do not use a CLA. Apache-2.0 already grants the patent rights we need, and DCO removes contribution friction (no off-platform forms).

Pull requests without DCO sign-off on every commit will be blocked by the `dco` status check. If you forgot, rebase and re-commit with `-s` or run `git commit --amend --signoff` then `git push -f`.

## Commit messages: Conventional Commits

Subjects follow [Conventional Commits 1.0](https://www.conventionalcommits.org/en/v1.0.0/):

```
<type>(<scope>)<!>: <description>
```

Where `<type>` is one of `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `build`, `ci`, `perf`. The optional `!` marks a breaking change.

Examples:

```
feat(openapi): add fl2v video mode to capabilities schema
fix(comfyui-loovie): handle missing seed in /images/create
docs(security): clarify localhost auth bypass
ci: pin all actions by SHA
feat(comfyui-loovie)!: rename ss_videos to videos in capabilities
```

`release-please` reads these to decide version bumps and write the CHANGELOG automatically once we're past `v0.1.0-beta`.

## Pull request flow

1. Fork the repo and create a topic branch off `main`.
2. Make your changes; sign off every commit; follow the commit message convention above.
3. Run the local checks (see "Dev setup" below) — CI runs them too.
4. Open a PR. Fill in the template. If you change the contract, you must also update the OpenAPI spec and bump `info.version`.
5. A maintainer reviews. Public discussion is preferred; for sensitive topics, see the security section below.
6. Once approved and all status checks pass, a maintainer squashes-and-merges. The squash subject must follow Conventional Commits.

## Dev setup

You need:

- Python 3.10, 3.11, or 3.12 (CI tests all three).
- [uv](https://github.com/astral-sh/uv) for fast Python environment management (recommended), or plain `pip` + `venv`.
- Node.js 20 (for OpenAPI tooling). `.nvmrc` is provided.
- Docker (optional, only for building the container).

For the reference ComfyUI implementation (once `v0.1.0-beta` lands):

```sh
cd comfyui-loovie
uv sync                       # creates .venv, installs everything from pyproject.toml
uv run ruff check             # lint
uv run ruff format --check    # format check
uv run mypy                   # type check (strict)
uv run pytest                 # unit tests
```

For the OpenAPI spec:

```sh
npx -y @redocly/cli lint openapi/loovie-server.openapi.yaml --extends=recommended-strict
```

For the FastAPI example:

```sh
cd examples/minimal-server
uv sync
uv run pytest
uv run uvicorn app:app --reload
```

## Contributing a workflow

If you want to add a new ComfyUI workflow (different model, variant, or mode) to `comfyui-loovie/workflows/`:

1. Author the workflow in ComfyUI; export in **API format** only (Settings → enable Dev mode options → ⋯ → Save (API Format)). We do not ship UI workflow JSON.
2. Include the relevant Loovie node `class_type`s in the workflow (`LoovieTextInput`, `LoovieSettings`, `LoovieImageInput`, `LoovieLoraStack`, etc.). The route layer injects request values by `class_type` — no param maps.
3. Add the workflow filename to `comfyui-loovie/config.yaml` under `workflows:`.
4. If your workflow advertises new modes, variants, resolutions, or aspect ratios, ensure they're in the OpenAPI's closed enums (or open a PR to extend them with a `schemaVersion` bump).
5. Add a test prompt + expected qualitative output to your PR description.
6. Use the [Workflow contribution](https://github.com/looviehq/loovie-community/issues/new?template=workflow_contribution.yml) issue template if you want to discuss first.
7. Note any upstream model license obligations in your PR.

## Reporting security issues

**Do not open a public issue.** See [SECURITY.md](SECURITY.md) for the responsible disclosure process.

## Code of Conduct

This project follows the [Contributor Covenant 2.1](CODE_OF_CONDUCT.md). Be excellent.
