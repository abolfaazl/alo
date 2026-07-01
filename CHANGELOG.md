# Changelog

## 1.1.2

Release hygiene patch after the v1.1.1 TestPyPI candidate.

- Clarifies LLM setup vs live connection verification in Settings.
- Improves safe connection-test diagnostics for authentication, model, timeout, and provider errors.
- Fixes connection-test result handling to use the correct `ServiceResult.payload` field.
- Keeps API keys and credentials hidden.
- No new features.

## 1.1.1

Release hygiene patch after the v1.1.0 TestPyPI candidate.

- Preserves user configuration more safely when config files are invalid or partial.
- Improves Settings trust messages and troubleshooting guidance.
- Keeps the public CLI command unchanged as `alo`.
- No new features.

## v1.1.0

### Added
- Learning stats engine for local workspace metrics.
- Workspace README generator via `alo readme`.
- Local SVG progress charts via `alo charts`.
- Portfolio README chart integration with `--include-charts`.
- Local gamification summary and milestone badges via `alo badges`.
- Optional README momentum section with `--include-gamification`.
- Workspace status summary via `alo status`.
- Dashboard support for portfolio commands and live status panel.

### Security
- Generated README and SVG outputs avoid raw Markdown dumps and sanitize secret-looking content.
- Git sync safe-list only allows known learning files, root `README.md`, and the four generated ALO SVG assets.

### Notes
- Roadmap import is not included in v1.1.0 and remains future work.

## v1.0.4
- Fixed PyPI Trusted Publishing workflow by declaring the `pypi` GitHub environment in the publish job.
- Supersedes v1.0.3 for real PyPI publishing.

## v1.0.3
- Public release candidate.
- Declares Python 3.12+ support.
- CI adjusted to the supported Python version.
- Real PyPI publish workflow gated to avoid accidental publish before Trusted Publishing setup.
- Added TestPyPI gate.

## v1.0.2
- Public GitHub preparation.
- Superseded by v1.0.3 due to CI/publish gating fixes.
- CLI command remains alo.

## v1.0.1
- Security patch: sanitized LLM provider/authentication errors to prevent API key fragments from appearing in CLI/dashboard output.

## v1.0.0
- Initial local release.
- Superseded by v1.0.1.
