# Toolixa Architecture

## System boundary

Toolixa has three distinct surfaces:

1. The public static Agent Directory at `https://toolixa-agents.vercel.app`.
2. The local Python AI Gateway, which a developer installs and runs on their own computer.
3. The experimental Python agent SDK and individual starter agents.

The static website does not execute Python agents and is not the gateway backend.

## Current local gateway flow

~~~text
PowerShell
  -> Python virtual environment
  -> install toolixa-core[gateway]
  -> python -m toolixa_core.gateway
  -> 127.0.0.1:20128 local dashboard
       -> local login
       -> provider endpoint + upstream API key
       -> encrypted SQLite credential store
       -> model discovery / playground
       -> issue a one-time Toolixa API key
  -> compatible SDK/client
       -> /v1/models
       -> /v1/chat/completions (JSON or SSE)
  -> OpenAI Chat Completions-compatible upstream endpoint
~~~

The gateway currently accepts any trusted provider endpoint that implements the OpenAI Chat Completions-compatible routes used by this integration. It is not a native implementation of every vendor protocol, and it does not yet execute MCP tools or orchestrate the six agent starters.

## Package boundaries

- `core/src/toolixa_core/contracts` defines request, result, manifest, and budget types.
- `providers` defines a provider-neutral protocol, explicit registry and factory.
- `gateway` contains the optional local FastAPI dashboard, SQLite store, encrypted credential vault, compatible HTTP adapter and OpenAI-compatible local API.
- `tools` defines metadata, context, and a registry that checks required permissions.
- `security` defines permission names, deny-by-default decisions, and ephemeral one-use approvals.
- `runtime` defines resource budgets and a disabled-by-default executor protocol.
- `memory` defines a storage protocol and source-aware document chunks.
- Each `agents/*` directory owns its entry point, manifest, README, tests, and direct dependencies.

The optional gateway dependencies are separate from the minimal SDK. The gateway is Python; its UI is server-rendered HTML/CSS and does not need a Node build or Go/Rust sidecar.

## Data flow and trust

Agent manifests are declarations, not grants. Runtime permissions are supplied by the operator for a request. Provider responses, fetched pages, and retrieved documents are untrusted data. They never become higher-priority instructions.

Provider credentials are entered in the local dashboard and encrypted in the local data store. Toolixa-issued API credentials are shown once and stored as hashes. The gateway binds to loopback and is intended for trusted local development only. It must not be exposed by a tunnel, public reverse proxy or port forwarding.

## Current gaps

- Starter agents do not yet automatically use the gateway.
- Native provider protocols, OAuth and arbitrary REST schemas are not implemented.
- MCP client/server integration and safe tool execution are not implemented.
- A production sandbox executor, vector database and browser automation are not included.
- The gateway has not completed independent penetration testing, full CSRF/rate-limit review, remote multi-tenant security or production operational review.

## Scaling roadmap

1. Local compatible gateway and encrypted BYOK configuration (experimental alpha).
2. Native provider adapters, MCP registry/client/server and permission-gated tool bridge.
3. Connect the gateway to agent runtime with per-agent model/tool policies.
4. Isolated execution, browser automation, source-aware vector memory and audit/observability.
5. Optional multi-user hosted service only after tenant isolation, remote secrets/KMS, identity, quotas, deployment and incident-response controls are designed and independently reviewed.

## Distribution

Install toolixa-core in editable mode for monorepo development with `python -m pip install -e ./core`. Add `[gateway]` only to run the local dashboard/API. Install only the chosen agent's direct requirements.

A standalone agent archive must pin or bundle a compatible core distribution; copying one folder while omitting its declared core dependency is not a complete release.
