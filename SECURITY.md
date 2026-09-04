# Security and privacy notes

This repository is a configuration guide. Do not publish a literal copy of your local Codex home.

## Never commit

- API keys
- access tokens / Bearer tokens
- OAuth credentials
- `.env` secrets
- private keys / PEM files
- browser cookies/profile state
- private database files
- raw diagnostic archives that can contain credentials
- raw CRG graph exports from private codebases without inspection

## Sanitize paths

Replace paths such as:

```text
C:\Users\real-name\...
C:\Company\PrivateProject\...
```

with generic examples:

```text
%USERPROFILE%\...
C:\path\to\repo
```

## Sanitize Codex config

A real `config.toml` can expose:

- private project paths
- plugin inventory
- local runtime IDs
- MCP endpoints
- Bearer-token environment variables
- browser/computer-use integration paths

Publish only minimal snippets.

## CRG exports

CRG stores its graph locally. Exports can include absolute paths and code-structure metadata. Treat them as potentially sensitive source artifacts.
