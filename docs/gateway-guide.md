# Toolixa Local AI Gateway Guide

**Status:** Experimental, single-user, loopback-only alpha.

## How the integration works

```text
PowerShell
  -> install Python package with [gateway] extra
  -> python -m toolixa_core.gateway
  -> local browser dashboard (127.0.0.1:20128)
       -> Add provider endpoint + provider API key
       -> Test connection and discover models
       -> Try a model in the playground
       -> Create a Toolixa client key
  -> compatible client / future Toolixa agents
       -> http://127.0.0.1:20128/v1
       -> GET /models
       -> POST /chat/completions
  -> selected upstream provider/model
```

Toolixa stores a provider/model pair under a namespaced ID: `provider-id/model-id`. The Toolixa client sends its own Toolixa gateway key; the server looks up the upstream provider credential and forwards the request.

## Install on Windows

Use Python 3.11 or newer and Git.

```powershell
git clone https://github.com/tasnimamin38/toolixa-agents.git
cd toolixa-agents
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".\core[gateway]"
python -m toolixa_core.gateway
```

On the first run, the terminal prints a randomly generated dashboard password once. Save it in a password manager. The dashboard opens automatically; otherwise visit `http://127.0.0.1:20128`. The server prints the actual URL and data directory on startup. Stop it with `Ctrl+C`.

To choose another local port:

```powershell
python -m toolixa_core.gateway --port 20129
```

## Add a model provider

In the dashboard, complete:

- **Name:** a label you recognise, for example `OpenRouter`, `Ollama local`, `LM Studio`, or `My inference server`.
- **API base URL:** the base path for an OpenAI Chat Completions-compatible API, usually ending with `/v1`.
- **API key:** the credential for that upstream. For a local server that does not require one, use a non-secret placeholder only if that server accepts a bearer header.
- **Models:** optional comma-separated model IDs. Use **Test connection** after saving to discover IDs from `GET {base_url}/models`.

Examples of compatible endpoint patterns:

| System | Example API base | Notes |
|---|---|---|
| OpenRouter | `https://openrouter.ai/api/v1` | Select a model ID accepted by your account |
| Ollama | `http://127.0.0.1:11434/v1` | Enable/use its OpenAI-compatible endpoint |
| LM Studio | `http://127.0.0.1:1234/v1` | Start its local server |
| vLLM | `http://127.0.0.1:8000/v1` | Keep local or private-network deployment protected |
| Other compatible server | `https://your-host.example/v1` | Must implement the compatible `/models` and `/chat/completions` routes |

Toolixa rejects plaintext HTTP to non-loopback hosts and rejects endpoint URLs containing embedded credentials, query strings or fragments. Provider connection requests do not follow redirects and do not inherit proxy environment variables.

## API usage

Create a Toolixa API key in the dashboard. It is shown only once. Keep it separate from the upstream provider key.

List configured models:

```http
GET /v1/models
Authorization: Bearer tla_YOUR_TOOLIXA_KEY
```

Send a chat completion:

```http
POST /v1/chat/completions
Authorization: Bearer tla_YOUR_TOOLIXA_KEY
Content-Type: application/json

{
  "model": "ollama-local/qwen2.5:7b",
  "messages": [
    {"role": "user", "content": "Explain this Python function."}
  ],
  "temperature": 0.2
}
```

Streaming uses `"stream": true` and proxies server-sent events. Client compatibility depends on the subset of the OpenAI Chat Completions contract implemented by the upstream provider.

## Local data and credentials

On Windows, by default the application stores data under:

```text
%LOCALAPPDATA%\Toolixa\gateway\
  gateway.sqlite3
  vault.key
```

Provider credentials are encrypted in SQLite with a Fernet key stored outside the Git repository. Toolixa API keys are shown once and stored as SHA-256 hashes. The dashboard password is stored as a salted scrypt hash. Keep the entire directory inside the protected user profile; do not upload it or commit it.

Encryption at rest is a layer of defence, not a protection against malware or an attacker who can read both the database and the vault key. Back up the database and key together only to an encrypted, access-controlled backup location. Losing the key makes stored provider credentials unreadable.

## Supported now versus planned

**Implemented in this alpha:** custom OpenAI-compatible upstreams; encrypted local provider-key storage; local dashboard login; API-key creation/revocation; model discovery; one-shot chat; streaming chat proxy; dashboard playground; API authentication; upstream-key redaction; localhost-only listener and trusted-host restrictions.

**Not implemented yet:** direct native adapters for all proprietary provider protocols; OAuth sign-in; arbitrary non-OpenAI-compatible REST schemas; MCP client/tool execution; agent tool calling; model-based multi-agent delegation; per-agent model policies; browser automation; remote multi-user access; high-availability or production-grade rate limiting and observability.

“Any model” therefore means any model exposed by an endpoint that speaks the supported compatible API, not literally every model or AI protocol. Other native protocols need an adapter or a compatible gateway in between.

## Security boundary

- The server binds to `127.0.0.1`, accepts only local Host headers, and does not enable CORS.
- Do not port-forward, tunnel, or reverse-proxy this dashboard/API to the public internet.
- The dashboard is protected by a local password and strict same-site HTTP-only session cookie.
- API routes require a Toolixa-issued bearer key. Revoke keys that are no longer needed.
- Provider URLs are entered by the local operator and must be trusted. Do not configure an unknown host or a service that should not receive prompts.
- A configured provider will receive the prompt and relevant conversation content. Review its privacy, retention and billing terms.
- Keep the machine, Windows account, Python environment and local data directory secured.

This alpha has not yet completed an independent penetration test, comprehensive CSRF/rate-limit review, or production multi-user threat model. It is for trusted local development and evaluation only.
