# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Once `v0.1.0-beta` ships, this file will be maintained automatically by [`release-please`](https://github.com/googleapis/release-please) driven by [Conventional Commits](https://www.conventionalcommits.org/).

> **Beta API stability.** While we are on the `0.x` line, the BYO HTTP contract (`openapi/loovie-server.openapi.yaml`) may introduce breaking changes between minor versions. Every breaking change is logged below and reflected in a bump of `info.version` on the spec (and `schemaVersion` on the capabilities manifest when the shape changes). Pin to a specific tag or commit SHA if you depend on the contract; strict semver kicks in at `1.0.0`.

## [0.4.0-beta.1](https://github.com/looviehq/loovie-community/compare/v0.3.0-beta.1...v0.4.0-beta.1) (2026-11-14)


### Features

* **comfyui-loovie:** add HyperFlow H3 Flash video model ([#94](https://github.com/looviehq/loovie-community/issues/94)) ([2428536](https://github.com/looviehq/loovie-community/commit/2428536a68f7b9233ea34494da48efcf462acf19))
* **comfyui-loovie:** add MiniMax H3 Image and bump ComfyUI to 0.45.0 ([#100](https://github.com/looviehq/loovie-community/issues/100)) ([f1b9892](https://github.com/looviehq/loovie-community/commit/f1b989231ddab34de804dc3e100f065ae6508ce6))
* **comfyui-loovie:** add Qwen-Image 2.1, FLUX 3 Klein and Krea 2 ([#95](https://github.com/looviehq/loovie-community/issues/95)) ([2d0d6e9](https://github.com/looviehq/loovie-community/commit/2d0d6e9b0f5f1d7166413bdcb5b6512938d086e5))
* **comfyui-loovie:** add reference audio to the BYO contract and manifest ([#103](https://github.com/looviehq/loovie-community/issues/103)) ([2979fd6](https://github.com/looviehq/loovie-community/commit/2979fd6448bb44b5470b3c78ff206801d5637622))
* **comfyui-loovie:** answer 400 with the real reason instead of retrying ([#101](https://github.com/looviehq/loovie-community/issues/101)) ([2c7f4ae](https://github.com/looviehq/loovie-community/commit/2c7f4ae505d40adbed40e541ee0287f102953e87))
* **comfyui-loovie:** multi-model BYO contract and Stable Audio 3 SFX ([#92](https://github.com/looviehq/loovie-community/issues/92)) ([761297b](https://github.com/looviehq/loovie-community/commit/761297ba3b107c8d7468765d899ab5739867c17c))
* **comfyui-loovie:** runnable Pika H3 Flex graphs ([#93](https://github.com/looviehq/loovie-community/issues/93)) ([5f9df45](https://github.com/looviehq/loovie-community/commit/5f9df4535614a28600d626464062f96c70c07722))


### Documentation

* **mcp:** align bundled skills with the current MCP tool surface ([#90](https://github.com/looviehq/loovie-community/issues/90)) ([a699c53](https://github.com/looviehq/loovie-community/commit/a699c531b7dbfa342e449cbbba768bedf592b554))

## [0.3.0-beta.1](https://github.com/looviehq/loovie-community/compare/v0.2.3-beta.1...v0.3.0-beta.1) (2026-10-17)


### Features

* **cli:** round out the installer — update command, --force, MCP + Claude Desktop registration fixes ([#39](https://github.com/looviehq/loovie-community/issues/39)) ([a39e2f1](https://github.com/looviehq/loovie-community/commit/a39e2f1e0e5f3aa3a3b252240b65d27021f6b91f))
* **comfyui-loovie:** reference ComfyUI implementation of the BYO contract ([7e3fe58](https://github.com/looviehq/loovie-community/commit/7e3fe58573dfc87ad7da74e3aa35f0f6ea292436))
* **docker:** reference Dockerfile + RunPod template + model downloader (A.6) ([b2081a4](https://github.com/looviehq/loovie-community/commit/b2081a4ee44026a81f98641278e78077e1bb9b46))
* **examples:** add framework-agnostic FastAPI minimal-server + Python + contract CI ([11fb689](https://github.com/looviehq/loovie-community/commit/11fb68913b7a7d0fb6ccd2cb6cc40e011cf5ec65))
* **music:** add YuE2 text-to-music capability to the BYO contract ([#80](https://github.com/looviehq/loovie-community/issues/80)) ([6feae38](https://github.com/looviehq/loovie-community/commit/6feae387365aeef767e6f106cc0dacf1bca5be9c))
* **openapi:** add normative BYO server contract (loovie-server v1.0.0-beta.1) ([cd6126c](https://github.com/looviehq/loovie-community/commit/cd6126cd1245d4e842c7e4fa383f3f91cee52f31))


### Bug Fixes

* align local schemathesis with CI, unblock release-please checks ([#18](https://github.com/looviehq/loovie-community/issues/18)) ([305ad33](https://github.com/looviehq/loovie-community/commit/305ad33414bc9578d37db6fcc45a43b19b3c4629))
* **ci:** hadolint DL3003 (WORKDIR) + DL3059 (consecutive RUNs) + markdownlint MD028/MD031 ([d6de853](https://github.com/looviehq/loovie-community/commit/d6de85300e95686e9c44bafa55ed4e2ae733735b))
* **ci:** let org members skip DCO sign-off so release PRs pass ([#84](https://github.com/looviehq/loovie-community/issues/84)) ([720cfef](https://github.com/looviehq/loovie-community/commit/720cfef288de481c71c832d0c54193742083001b))
* **ci:** resolve cli extra-files from repo root so plugin versions bump ([#82](https://github.com/looviehq/loovie-community/issues/82)) ([66803fd](https://github.com/looviehq/loovie-community/commit/66803fd2fafa8b548c9ae510ccac3b8f4aefc4a0))
* **ci:** ruff format comfyui-loovie + pin schemathesis to &lt;4 ([ff411b6](https://github.com/looviehq/loovie-community/commit/ff411b67828206dcba76cd91df1e3114a0cc9418))
* **ci:** stop markdownlint and lychee failing release-please PRs ([#83](https://github.com/looviehq/loovie-community/issues/83)) ([c629e0a](https://github.com/looviehq/loovie-community/commit/c629e0abc77f5e3e4a26ba1dca4d0010477ba419))
* **ci:** use uv venv on minimal-server + enable schemathesis openapi-3.1 ([ba37419](https://github.com/looviehq/loovie-community/commit/ba374194665e9fe4b9c1442f05c8573f95384f98))
* **comfyui-loovie:** mypy --strict clean (28 → 0 errors) ([#8](https://github.com/looviehq/loovie-community/issues/8)) ([1441614](https://github.com/looviehq/loovie-community/commit/144161445f7e1bf7f506b54baf3c9a2544be9a44))
* **examples:** minimal-server returns 400 on bad input + Annotated form deps + line-length ([d17ccfe](https://github.com/looviehq/loovie-community/commit/d17ccfe187872263baf9ba63e237a5ca4c3113ef))
* **mcp:** correct stale skill facts and align skills with authoring best practices ([#49](https://github.com/looviehq/loovie-community/issues/49)) ([e506435](https://github.com/looviehq/loovie-community/commit/e5064354d0fa021601bba60249a7896c47f5a197))
* **models:** real HF repos, manifest path, node entrypoints ([#19](https://github.com/looviehq/loovie-community/issues/19)) ([7b9ef8d](https://github.com/looviehq/loovie-community/commit/7b9ef8d6be63f74a176afd245dcb61450bcc95d7))
* **workflows:** correct LTX 2.3 graphs and reduce artifacts ([#16](https://github.com/looviehq/loovie-community/issues/16)) ([04fa449](https://github.com/looviehq/loovie-community/commit/04fa449f7cd41df908886cb048e38fe8a7a80255))


### Documentation

* fix markdownlint issues in governance files ([6f0d62a](https://github.com/looviehq/loovie-community/commit/6f0d62a2d55286ad8e9bd47915938d74044b323f))
* **mcp:** asset-host allowlist guidance + inline-preview fallback ([#31](https://github.com/looviehq/loovie-community/issues/31)) ([296ade2](https://github.com/looviehq/loovie-community/commit/296ade2812afc55f274a0a144386a184c1a8c94b))
* **mcp:** bake downsize-before-upload guidance into skills ([#29](https://github.com/looviehq/loovie-community/issues/29)) ([165b9bf](https://github.com/looviehq/loovie-community/commit/165b9bf40053ddd395033235033fdcb66cb583f0))
* **mcp:** downsize-before-upload guidance across skills ([#32](https://github.com/looviehq/loovie-community/issues/32)) ([f1c5985](https://github.com/looviehq/loovie-community/commit/f1c5985fd89a99ab1fdee5dde645d28940d0097f))
* **mcp:** reference-driven video and one-approval spend flow in skills ([#72](https://github.com/looviehq/loovie-community/issues/72)) ([0ed76f1](https://github.com/looviehq/loovie-community/commit/0ed76f1bde921240bb8fcc95eca9fd6bc2ffd895))
* **openapi:** add 400/422 responses to POST endpoints ([4cd3a71](https://github.com/looviehq/loovie-community/commit/4cd3a7107582d1e3de1d909a1c65b8a2611eac65))
* **openapi:** document the full failCode taxonomy ([#3](https://github.com/looviehq/loovie-community/issues/3)) ([0567fc7](https://github.com/looviehq/loovie-community/commit/0567fc7fc984840496f903181365a0736bff0fbd))
* prominent beta API stability warning across README, CHANGELOG, OpenAPI ([b42c62a](https://github.com/looviehq/loovie-community/commit/b42c62a1a794f16161a704ba263729282f7f2542))
* remove internal backend implementation details ([#5](https://github.com/looviehq/loovie-community/issues/5)) ([75e2658](https://github.com/looviehq/loovie-community/commit/75e26585c343e906ef13c965afda02362e0c591f))
* ship 14-file self-host guide for the BYO public beta ([5e75bb8](https://github.com/looviehq/loovie-community/commit/5e75bb84e54a77061629d42d1ead7222cf8f3595))
* tighten privacy wording — Loovie backend + staff, not bare "Loovie" ([bf8b1d0](https://github.com/looviehq/loovie-community/commit/bf8b1d0b0e1b6a83ad929b10fa3ca52696a04194))


### Tests

* **comfyui-loovie:** 127 unit tests + 88% coverage on pure-logic modules ([03ea456](https://github.com/looviehq/loovie-community/commit/03ea4566aa4babf4867d2627b4a48ed7867e5b2f))
* **minimal-server:** annotate fake_require_bearer request param as Request ([4111350](https://github.com/looviehq/loovie-community/commit/41113507246015ab4b457aa25de5dc9bca35b3d7))


### Features

* **comfyui-loovie:** model-aware BYO contract (capabilities `schemaVersion: 2`). A new top-level `models` map (`images`, `ss_videos`) advertises each enabled model with its own modes, variants, reference limits, audio policy and VRAM hints. Requests gain `model` + model-scoped `variant`; `/videos/create` gains `ref2v` + `reference_image_urls`.
* **comfyui-loovie:** LTX 2.5 is the default single-shot video model (t2v/i2v/fl2v fast, validated on a GB10); LTX 2.3 remains a legacy/pro opt-in.
* **comfyui-loovie:** model registry with a built-in catalogue for FLUX.2 Klein, Qwen-Image 2.1, FLUX 3 Klein, Krea 2, MOSS-Image, LTX 2.3, LTX 2.5, Pika H3 Flex and Pika H3 Flex HD. A model is advertised only when its workflow is registered and the model is enabled; partial installs narrow modes/variants.
* **comfyui-loovie:** `models.enabled` / `models.defaults` in `config.yaml`, a `models.switch_policy` (`auto|always|never`), and explicit ComfyUI model-group unloading on a switch that does not fit. Never unloads after every generation or while another task is processing.
* **comfyui-loovie:** YuE2 text-to-music reference workflow + `music` capability section (`/music/create`, `/music/status`, `LoovieMusicInput` node, `LoovieMusicInput` injection), music model manifest entry, and `LOOVIE_KIND=music` download selection.

### Documentation

* **openapi:** bump to `0.4.0-beta.1` and `schemaVersion: 2`; add `Models`, `ImageModel`, `VideoModel`, `ModelVariant`, `AudioPolicy` and `Hardware`; widen resolutions/aspect ratios; document `ref2v`, `reference_image_urls`, model-scoped variants and the v1 compatibility view.
* **docs:** model catalogue, VRAM planning table, Pika H3 Flex / LTX 2.5 / Qwen 2.1 / FLUX 3 Klein / Krea 2 / MOSS-Image licence notes, and the model-switch policy.
* **docs:** note the YuE2 model-licence responsibility for company-operated servers.

## [0.2.3-beta.1](https://github.com/looviehq/loovie-community/compare/v0.2.2-beta.1...v0.2.3-beta.1) (2026-05-30)


### Documentation

* **mcp:** asset-host allowlist guidance + inline-preview fallback ([#31](https://github.com/looviehq/loovie-community/issues/31)) ([296ade2](https://github.com/looviehq/loovie-community/commit/296ade2812afc55f274a0a144386a184c1a8c94b))
* **mcp:** bake downsize-before-upload guidance into skills ([#29](https://github.com/looviehq/loovie-community/issues/29)) ([165b9bf](https://github.com/looviehq/loovie-community/commit/165b9bf40053ddd395033235033fdcb66cb583f0))

## [0.2.2-beta.1](https://github.com/looviehq/loovie-community/compare/v0.2.1-beta.1...v0.2.2-beta.1) (2026-05-27)


### Bug Fixes

* align local schemathesis with CI, unblock release-please checks ([#18](https://github.com/looviehq/loovie-community/issues/18)) ([305ad33](https://github.com/looviehq/loovie-community/commit/305ad33414bc9578d37db6fcc45a43b19b3c4629))
* **models:** real HF repos, manifest path, node entrypoints ([#19](https://github.com/looviehq/loovie-community/issues/19)) ([7b9ef8d](https://github.com/looviehq/loovie-community/commit/7b9ef8d6be63f74a176afd245dcb61450bcc95d7))
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

- **comfyui-loovie:** Pika H3 Flex is runnable in the reference server:
  official/turbo t2v/i2v/fl2v/ref2v, HD t2v/i2v/fl2v, a dynamic
  `LoovieH3ReferenceToVideo` adapter for 0–9 references, and ComfyUI base/LoRA
  manifest entries.
- **comfyui-loovie:** sound effects are a first-class modality (`t2s`): Stable
  Audio 3 Small SFX (`checkpoints/stable_audio_3_small_sfx.safetensors` +
  `t5gemma_b_b_ul2`), `/sfx/create` + `/sfx/status`, `models.sfx` capabilities,
  and the `LoovieSfxInput` node.
- **comfyui-loovie:** 384p/480p/540p/768p/2K video dimensions are in the
  resolution table; LTX 2.5 advertises 540p/720p/1080p/2K (its distilled
  transformer rejects lower latents), while Pika H3 keeps 384p/480p/540p/768p.
- **comfyui-loovie:** silent LTX 2.5 renders no longer fail with a tensor-size
  mismatch — the audio latent is always sized to the clip and the
  `LoovieAudioGate` node drops the track after decode.
- Initial repository scaffold: LICENSE (Apache-2.0), NOTICE, README, CHANGELOG, CONTRIBUTING (DCO), CODE_OF_CONDUCT (Contributor Covenant 2.1), SECURITY, LEGAL.
- `.github/` issue forms (bug, feature, spec change), PR template, Dependabot configuration.
- Standard editor and Git configuration (`.editorconfig`, `.nvmrc`, `.gitignore`).
