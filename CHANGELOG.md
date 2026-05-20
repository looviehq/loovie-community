# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Once `v0.1.0-beta` ships, this file will be maintained automatically by [`release-please`](https://github.com/googleapis/release-please) driven by [Conventional Commits](https://www.conventionalcommits.org/).

> **Beta API stability.** While we are on the `0.x` line, the BYO HTTP contract (`openapi/loovie-server.openapi.yaml`) may introduce breaking changes between minor versions. Every breaking change is logged below and reflected in a bump of `info.version` on the spec (and `schemaVersion` on the capabilities manifest when the shape changes). Pin to a specific tag or commit SHA if you depend on the contract; strict semver kicks in at `1.0.0`.

## [Unreleased]

### Added

- Initial repository scaffold: LICENSE (Apache-2.0), NOTICE, README, CHANGELOG, CONTRIBUTING (DCO), CODE_OF_CONDUCT (Contributor Covenant 2.1), SECURITY, LEGAL.
- `.github/` issue forms (bug, feature, spec change), PR template, Dependabot configuration.
- Standard editor and Git configuration (`.editorconfig`, `.nvmrc`, `.gitignore`).
