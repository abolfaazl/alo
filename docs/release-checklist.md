# ALO Release Checklist

Before tagging and releasing a new version of ALO, run through the following checks to ensure code quality, packaging correctness, and security.

## Automated Checks
- [ ] `compileall passes`
- [ ] `pytest passes`
- [ ] `ruff passes`

## Packaging & Installation
- [ ] `alo --help` works
- [ ] `alo doctor` works
- [ ] `alo version` and `alo --version` work and match the expected release version.
- [ ] Package data (`mimo.css`) is properly bundled in the release.

## UI & Core Flows
- [ ] Dashboard opens correctly (`alo home`).
- [ ] `init` works in a clean temporary workspace.
- [ ] `config` does not expose API keys (only keyring/env details).
- [ ] `paths --mock` works.
- [ ] `roadmap --mock` works.
- [ ] `learn --mock` works.
- [ ] `review --mock` works.

## Git Sync & Safety
- [ ] `sync --dry-run` works.
- [ ] `sync` safely refuses to run on the ALO source repository.

## Security
- [ ] Secret scan blocks fake/raw API keys. Docs contain absolutely no raw secret strings.

## Patch Notes
- v1.0.1: Security patch — sanitized LLM provider authentication errors to prevent API key fragments from appearing in CLI/dashboard output.

## PyPI Release Checklist
1. git status clean
2. compileall / pytest / ruff / smoke test pass
3. docs security scan pass
4. build pass
5. twine check pass
6. TestPyPI publish
7. TestPyPI install
8. GitHub release
9. PyPI publish through Trusted Publishing
10. pip install alo-learning-os
11. alo version
12. alo doctor
