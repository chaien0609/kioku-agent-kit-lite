# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | ✅ Current release |

## Reporting a Vulnerability

If you discover a security vulnerability in kioku-lite, please report it responsibly:

1. **Do NOT** open a public GitHub issue for security vulnerabilities.
2. **Email** the maintainer at: **phuc.nt.dev@gmail.com**
3. Include a detailed description of the vulnerability and steps to reproduce it.
4. Allow reasonable time for a fix before public disclosure.

## Scope

kioku-lite is designed to run **locally** on a user's machine. It stores data in local SQLite databases and markdown files. It does **not** make external network calls (except for the initial one-time embedding model download).

Security considerations:
- **Data at rest:** Memory data is stored unencrypted in `~/.kioku-lite/`. Users are responsible for securing their own filesystem.
- **No authentication:** kioku-lite is a single-user local tool. There is no built-in authentication or authorization layer.
- **No external API calls:** The core engine never calls external APIs. The agent using kioku-lite may call LLMs separately, but that is outside kioku-lite's scope.

## Response Timeline

- **Acknowledgment:** Within 48 hours
- **Initial assessment:** Within 1 week
- **Fix release:** As soon as practical, depending on severity
