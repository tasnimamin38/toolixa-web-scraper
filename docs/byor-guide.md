# Bring Your Own Runtime (BYOR) and Bring Your Own Key (BYOK)

## BYOR

BYOR means the developer chooses where the agent process runs: a local virtual environment, a developer-managed container, or an independently operated server. Toolixa does not supply a central execution service.

The local gateway is a Python process operated by the developer. The current local app binds to loopback only. It is not a public service, multi-user control plane, or hardened remote executor.

The initial release does not include a production sandbox executor. Shell execution is disabled by default. Do not run untrusted code on a workstation that contains personal files, production credentials, or privileged cloud access.

## BYOK

BYOK means provider credentials are supplied by the operator, not embedded in Toolixa. In the local gateway, add an upstream API key in the browser dashboard. The server encrypts that key in its local SQLite store and decrypts it only to make an upstream call.

The gateway stores its local encryption key separately from the SQLite database in the user's application-data directory. Toolixa gateway client keys are shown once and stored as hashes. The dashboard bootstrap password is printed only on first initialization and stored as a salted scrypt hash. This is local at-rest protection, not a defence against malware or another process running as the same Windows/macOS/Linux user. Keep the local data directory private and never commit it.

Never paste credentials into chat, commit actual keys, print the environment, or serialize credentials into request objects.

## Development installation

1. Create a Python 3.11+ virtual environment.
2. Install the minimal SDK with `python -m pip install -e ./core`.
3. To run the local dashboard/API, install `python -m pip install -e "./core[gateway]"`.
4. Install only the chosen agent's requirements.
5. Read the selected agent README and manifest.
6. Start with a temporary workspace and no optional permissions.
7. Add a provider in the local dashboard only when a model-backed operation needs one.

## Provider compatibility boundary

The local gateway currently implements the OpenAI Chat Completions-compatible surface for model listing, non-streaming chat and streaming chat. It accepts any upstream service that implements the needed compatible routes. This can include a model host or a router such as OpenRouter, or a local runtime such as Ollama or LM Studio when configured with its compatible API.

This does not mean every native AI protocol is already supported. Native Anthropic/Gemini protocols, OAuth, arbitrary REST schemas, MCP client/tool execution, per-agent model selection and model-driven multi-agent delegation are separate planned adapters.

A missing provider configuration must produce an explicit error; no hidden fallback to a different provider is allowed. Do not configure untrusted endpoints: the configured provider receives prompts and conversation content and may have its own retention, privacy and billing terms.

## Python-first implementation

The shared agent contracts, gateway, storage, authentication, HTTP provider adapter, and server are Python. The dashboard uses server-rendered HTML templates and CSS; no Node.js, Go or Rust service is required to run it. Add a lower-level language only when profiling proves Python is the limiting factor and the added build/deployment complexity is justified.
