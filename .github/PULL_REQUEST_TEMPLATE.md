<!--
Thanks for the contribution! A few things to confirm before we merge:
-->

## Summary

<!-- One or two sentences. What does this change do, and why? -->

## Linked issue

<!-- e.g. Closes #123, Relates to #456. If no issue exists, briefly explain context. -->

## Type of change

- [ ] `feat` — new user-facing feature
- [ ] `fix` — bug fix
- [ ] `docs` — documentation only
- [ ] `refactor` — code change without behavioural change
- [ ] `test` — tests only
- [ ] `build`/`ci` — build system or CI
- [ ] `perf` — performance improvement
- [ ] `chore` — other (no version bump)
- [ ] **Breaking change** (suffix the commit type with `!` and explain in body)

## Checklist

- [ ] My commits are signed off (`git commit -s`) per the [DCO](../CONTRIBUTING.md#sign-off-dco-not-a-cla).
- [ ] My commit subjects follow [Conventional Commits](https://www.conventionalcommits.org/).
- [ ] I ran `ruff check` and `ruff format --check` locally (Python changes).
- [ ] I added or updated tests where appropriate.
- [ ] If this changes the contract: I updated `openapi/loovie-server.openapi.yaml` and bumped `info.version`.
- [ ] If this adds a workflow or model: I documented the model license in `docs/MODELS.md`.
- [ ] If this adds dependencies: I added them via the appropriate manifest, not hand-edited.
- [ ] CHANGELOG: nothing to do here — `release-please` will write it from my commit message.

## Test plan

<!-- How did you verify this works? What commands did you run? -->

## Notes for reviewers

<!-- Anything reviewers should know that isn't obvious from the diff. -->
