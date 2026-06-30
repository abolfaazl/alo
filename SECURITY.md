# Security Policy

## Supported Versions

Only the latest release (`v1.x`) is supported with security updates.

## Reporting a Vulnerability

If you discover a security vulnerability in ALO, please **do not** report it by opening a public issue on GitHub. Instead, please report it privately to the maintainers if possible.

## API Key Security

ALO is designed to securely manage LLM credentials.
- **Do not** paste your API keys into GitHub issues or pull requests.
- ALO stores keys securely using your operating system's native keychain (via `keyring`) or allows you to use environment variables.
- **No raw API keys** should ever be committed to the repository, including `.env` files or workspaces in version control.
