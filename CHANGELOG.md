# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Once `v0.1.0-beta` ships, this file will be maintained automatically by [`release-please`](https://github.com/googleapis/release-please) driven by [Conventional Commits](https://www.conventionalcommits.org/).

> **Beta API stability.** While we are on the `0.x` line, the BYO HTTP contract (`openapi/loovie-server.openapi.yaml`) may introduce breaking changes between minor versions. Every breaking change is logged below and reflected in a bump of `info.version` on the spec (and `schemaVersion` on the capabilities manifest when the shape changes). Pin to a specific tag or commit SHA if you depend on the contract; strict semver kicks in at `1.0.0`.

## [0.2.2-beta.1](https://github.com/looviehq/loovie-community/compare/v0.2.1-beta.1...v0.2.2-beta.1) (2026-05-22)


### Bug Fixes

* **workflows:** correct LTX 2.3 graphs and reduce artifacts ([#16](https://github.com/looviehq/loovie-community/issues/16)) ([04fa449](https://github.com/looviehq/loovie-community/commit/04fa449f7cd41df908886cb048e38fe8a7a80255))

## [0.2.1-beta.1](https://github.com/looviehq/loovie-community/compare/v0.2.0-beta.1...v0.2.1-beta.1) (2026-05-20)


### Bug Fixes

* **comfyui-loovie:** mypy --strict clean (28 → 0 errors) ([#8](https://github.com/looviehq/loovie-community/issues/8)) ([1441614](https://github.com/looviehq/loovie-community/commit/144161445f7e1bf7f506b54baf3c9a2544be9a44))


### Documentation

* **openapi:** document the full failCode taxonomy ([#3](https://github.com/looviehq/loovie-community/issues/3)) ([0567fc7](https://github.com/looviehq/loovie-community/commit/0567fc7fc984840496f903181365a0736bff0fbd))
* remove internal backend implementation details ([#5](https://github.com/looviehq/loovie-community/issues/5)) ([75e2658](https://github.com/looviehq/loovie-community/commit/75e26585c343e906ef13c965afda02362e0c591f))

## [0.2.0-beta.1](https://github.com/looviehq/loovie-community/compare/v0.1.0-beta.1...v0.2.0-beta.1) (2026-05-20)


### Features

* **comfyui-loovie:** reference ComfyUI implementation of the BYO contract ([7e3fe58](https://github.com/looviehq/loovie-community/commit/7e3fe58573dfc87ad7da74e3aa35f0f6ea292436))
* **docker:** reference Dockerfile + RunPod template + model downloader (A.6) ([b2081a4](https://github.com/looviehq/loovie-community/commit/b2081a4ee44026a81f98641278e78077e1bb9b46))
* **examples:** add framework-agnostic FastAPI minimal-server + Python + contract CI ([11fb689](https://github.com/looviehq/loovie-community/commit/11fb68913b7a7d0fb6ccd2cb6cc40e011cf5ec65))
* **openapi:** add normative BYO server contract (loovie-server v1.0.0-beta.1) ([cd6126c](https://github.com/looviehq/loovie-community/commit/cd6126cd1245d4e842c7e4fa383f3f91cee52f31))


### Bug Fixes

* **ci:** hadolint DL3003 (WORKDIR) + DL3059 (consecutive RUNs) + markdownlint MD028/MD031 ([d6de853](https://github.com/looviehq/loovie-community/commit/d6de85300e95686e9c44bafa55ed4e2ae733735b))
* **ci:** ruff format comfyui-loovie + pin schemathesis to &lt;4 ([ff411b6](https://github.com/looviehq/loovie-community/commit/ff411b67828206dcba76cd91df1e3114a0cc9418))
* **ci:** use uv venv on minimal-server + enable schemathesis openapi-3.1 ([ba37419](https://github.com/looviehq/loovie-community/commit/ba374194665e9fe4b9c1442f05c8573f95384f98))
* **examples:** minimal-server returns 400 on bad input + Annotated form deps + line-length ([d17ccfe](https://github.com/looviehq/loovie-community/commit/d17ccfe187872263baf9ba63e237a5ca4c3113ef))


### Documentation

* fix markdownlint issues in governance files ([6f0d62a](https://github.com/looviehq/loovie-community/commit/6f0d62a2d55286ad8e9bd47915938d74044b323f))
* **openapi:** add 400/422 responses to POST endpoints ([4cd3a71](https://github.com/looviehq/loovie-community/commit/4cd3a7107582d1e3de1d909a1c65b8a2611eac65))
* prominent beta API stability warning across README, CHANGELOG, OpenAPI ([b42c62a](https://github.com/looviehq/loovie-community/commit/b42c62a1a794f16161a704ba263729282f7f2542))
* ship 14-file self-host guide for the BYO public beta ([5e75bb8](https://github.com/looviehq/loovie-community/commit/5e75bb84e54a77061629d42d1ead7222cf8f3595))
* tighten privacy wording — Loovie backend + staff, not bare "Loovie" ([bf8b1d0](https://github.com/looviehq/loovie-community/commit/bf8b1d0b0e1b6a83ad929b10fa3ca52696a04194))


### Tests

* **comfyui-loovie:** 127 unit tests + 88% coverage on pure-logic modules ([03ea456](https://github.com/looviehq/loovie-community/commit/03ea4566aa4babf4867d2627b4a48ed7867e5b2f))
* **minimal-server:** annotate fake_require_bearer request param as Request ([4111350](https://github.com/looviehq/loovie-community/commit/41113507246015ab4b457aa25de5dc9bca35b3d7))

## [Unreleased]

### Added

- Initial repository scaffold: LICENSE (Apache-2.0), NOTICE, README, CHANGELOG, CONTRIBUTING (DCO), CODE_OF_CONDUCT (Contributor Covenant 2.1), SECURITY, LEGAL.
- `.github/` issue forms (bug, feature, spec change), PR template, Dependabot configuration.
- Standard editor and Git configuration (`.editorconfig`, `.nvmrc`, `.gitignore`).
