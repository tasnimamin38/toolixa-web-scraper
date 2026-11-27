# Development Guide

## Repository layout

- `core/` contains provider-neutral contracts, safety primitives, and the optional local AI gateway.
- `core/src/toolixa_core/gateway/` contains the Python dashboard/API, local encrypted store, and OpenAI-compatible provider transport.
- `agents/` contains independent agent starters and manifests.
- `catalog/` contains generated website data.
- `scripts/` contains repository maintenance scripts.
- `tests/` contains core, agent, catalog, static-site and gateway checks.
- `docs/` contains architecture and operational guidance.

## Environment setup

~~~powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e "./core[gateway]"
python -m pip install "pytest>=9.0.3,<10" "ruff>=0.8,<1"
python -m pip install -r agents/06-web-scraper/requirements.txt
~~~

The base `toolixa-core` package has no mandatory third-party runtime dependencies. The optional `gateway` extra installs the packages needed for the local dashboard and API.

## Run and test the local gateway

~~~powershell
python -m toolixa_core.gateway --no-open
~~~

By default it binds to `127.0.0.1:20128`. The local provider API key is configured from the browser dashboard, not hard-coded or passed to tests. Gateway contract tests use `httpx.MockTransport` and do not make live provider calls.

Never expose this experimental local dashboard/API to the public internet.

## Add an agent

1. Create a uniquely named folder under `agents/`.
2. Add `main.py`, `agent.json`, `README.md`, `requirements.txt`, and `.env.example`.
3. Use only canonical permission identifiers from core. A manifest declaration does not grant access.
4. Keep optional/heavy dependencies inside that agent.
5. Add focused tests under `tests/agents`.
6. Regenerate `catalog/agents.json` with `python scripts/build_catalog.py`.
7. Run all checks before committing.

The catalog builder validates relative entry-point/documentation paths and known permission names. It does not import or run agent code.

## Local quality checks

~~~powershell
python -m compileall -q core/src agents scripts tests
ruff check core/src agents scripts tests
ruff format --check core/src agents scripts tests
python scripts/build_catalog.py --check
python -m pytest -q
~~~

## Pull requests and CI

GitHub Actions runs compile, lint, formatting, catalog consistency, tests, and dependency auditing of the declared runtime dependency trees. CI does not require provider API keys or perform active network scans.

## Security review checklist

- Does the new agent request only the permissions it needs?
- Are paths constrained to selected workspaces?
- Does network access have exact host policy and an enforced egress boundary?
- Are redirects and DNS resolution handled safely?
- Are secrets omitted from logs, errors, manifests, and artifacts?
- Are tool results and retrieved data treated as untrusted?
- Is shell/process execution absent unless an approved isolated executor exists?
- Are tests deterministic and free of uncontrolled external requests?
- Does any dashboard/API change include authentication, CSRF, session and rate-limit considerations?
- Are gateway URLs supplied only by a trusted local operator until DNS pinning/egress controls exist?

## Current limitations

The initial executor always denies process execution. The Web Scraper parses local HTML only. Content Maestro does not browse. RAG uses lexical retrieval. Aegis performs passive local pattern checks. Task Orchestrator orders dependencies but does not launch agents.

The local gateway currently accepts OpenAI Chat Completions-compatible upstream APIs. It does not yet implement every native vendor API, MCP client/tool execution, or automatic model wiring for each agent. It is an experimental, single-user, loopback-only alpha; a complete independent security review is still required before public deployment or production use.
