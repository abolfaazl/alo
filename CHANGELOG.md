# Changelog

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
