# Toolixa Security Model

## Threat model

Toolixa agents and gateway may process untrusted source files, HTML, retrieved documents, prompts, provider responses, task descriptions, API credentials, and URLs. Risks include prompt injection, accidental data disclosure, path traversal, SSRF, excessive execution, secret leakage, replay/CSRF, and unsafe agent delegation.

## Defaults

- No permission is granted merely because a manifest declares it.
- No shell/process execution is available through the default executor.
- Active security scanning is disabled unless an explicit target grant is provided.
- Workspace read/write operations must be constrained to operator-configured roots.
- Network access requires an explicit permission and exact host allowlist in the agent tool policy.
- Provider credentials must not appear in source, manifests, catalogs, logs, traces, or reports.
- The first Web Scraper parses local HTML files; it does not make HTTP requests.
- The local gateway binds to `127.0.0.1`, does not enable CORS, and restricts accepted Host headers to loopback/test hosts. Do not tunnel or expose it publicly.

## Permission names

`workspace.read`, `workspace.write`, `network.http`, `process.execute`, `browser.automate`, `security.scan.passive`, `security.scan.active`, `provider.invoke`, `memory.read`, and `memory.write` are canonical capability names.

Grants are request-scoped. The tool registry checks required permissions before invoking a registered tool. Tools that access a specific path or URL must additionally check the actual target. Active scan permission is bound to an allowlisted target.

## Local gateway credentials

- The first-run dashboard password is random, displayed once in the terminal, and stored as a salted scrypt hash.
- Upstream provider API keys are encrypted in SQLite with Fernet. The encryption key is kept separately in the user's local application-data directory (Windows: `%LOCALAPPDATA%\Toolixa\gateway\vault.key`).
- Toolixa gateway API keys use a random `tla_` token. The raw value is shown once; the DB retains its SHA-256 hash for authentication.
- Do not commit or upload either the database or vault key. If the key is lost, stored provider credentials cannot be decrypted.
- This at-rest protection only helps when an attacker gets the database without the key. Malware or another process operating as the same user can potentially access both. It is not an OS-level secret manager or a remote KMS.

## Local gateway limitations

This is an experimental, single-user, loopback-only alpha. It has not completed an independent penetration test, full CSRF and rate-limit hardening, tamper-evident audit logging, remote secret-manager integration, multi-tenant isolation, or high-availability review. Session cookies are HTTP-only and SameSite Strict, with trusted-host checks, but this must not be treated as a complete production web security review. Do not expose the dashboard or API over a public network.

The configured upstream provider receives prompts and conversation contents. Configure only providers you trust, and review their privacy, retention and billing terms. The gateway proxies the OpenAI Chat Completions-compatible surface only; proprietary native APIs and MCP tools are not yet integrated.

## Approvals

ApprovalManager provides in-process, short-lived, single-use tokens bound to one action and target. It is a building block, not an identity provider or durable approval database. Applications that need remote or persistent approvals must provide their own authenticated approval system.

## Execution isolation

DisabledExecutor is the only built-in executor. It always refuses process execution. Any future executor adapter must document and enforce its isolation boundary, non-root identity, read-only mounts where possible, CPU/memory/process/time limits, restricted network egress, and secret isolation.

A container alone is not a complete security boundary. Do not mount the Docker socket, host credentials, home directory, or privileged host resources into an agent container.

## SSRF and web fetching

Network-enabled crawling is deliberately not implemented in this baseline. A future HTTP fetcher must pin the validated resolved address to the actual connection or rely on an enforced egress proxy/firewall, re-check every redirect, reject loopback/private/link-local/multicast/reserved/metadata addresses, and test DNS rebinding. A preflight DNS lookup followed by an ordinary second DNS lookup in the HTTP client is not sufficient.

The current local gateway's upstream URLs are supplied by the local operator and are trusted configuration. It rejects embedded URL credentials and plaintext HTTP to non-loopback hosts, disables automatic redirects, and disables proxy environment inheritance. These checks do not replace address pinning for a future remotely configurable endpoint feature.

## RAG prompt injection

Retrieved passages are untrusted content. Keep system policy separate from retrieved text, show document source ranges, and never execute instructions embedded in documents.

## Logging

Use the redaction helper as one layer only. Avoid logging full request bodies, environment dumps, authorization headers, or source lines that may contain secrets. The local approval manager and logs are not tamper-proof.
