<div align="center">
  <img src="assets/readme-hero.svg" alt="Toolixa Agents — a local-first ecosystem for modular AI agents" width="100%" />

  <p><strong>Build, connect and operate modular AI agents with your own models, tools and runtime.</strong></p>

  <p>
    <a href="https://github.com/tasnimamin38/toolixa-agents/actions/workflows/ci.yml"><img src="https://github.com/tasnimamin38/toolixa-agents/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI status" /></a>
    <a href="https://github.com/tasnimamin38/toolixa-agents/actions/workflows/security.yml"><img src="https://github.com/tasnimamin38/toolixa-agents/actions/workflows/security.yml/badge.svg?branch=main" alt="Dependency security status" /></a>
    <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+" />
    <img src="https://img.shields.io/badge/Architecture-Local--first-16A085" alt="Local-first architecture" />
    <img src="https://img.shields.io/badge/Stage-Experimental-orange" alt="Experimental alpha" />
    <img src="https://img.shields.io/badge/License-Not%20selected-lightgrey" alt="No license selected" />
  </p>

  <p>
    <a href="https://toolixa-agents.vercel.app/">Live Agent Directory</a> ·
    <a href="#architecture">Architecture</a> ·
    <a href="#quick-start">Quick start</a> ·
    <a href="https://github.com/tasnimamin38/toolixa-agents/blob/feature/python-local-ai-gateway/docs/gateway-guide.md">Gateway guide</a> ·
    <a href="#roadmap">Roadmap</a>
  </p>
</div>

---

## Project at a glance

Toolixa Agents is evolving from a static agent directory and Python starter SDK into a **local-first AI gateway and agent runtime**. You bring the provider accounts, API credentials and machine or server that runs the agents. Toolixa provides the modular contracts and control layers.

| Principle | What it means |
|---|---|
| **BYOK** | Use API keys and accounts from providers you choose |
| **BYOR** | Run the gateway and agents in an environment you control |
| **Python-first** | Agent logic, gateway, orchestration and policy are Python |
| **Modular** | Providers, tools, memory and agents are separate integration surfaces |
| **Deny by default** | Declared capabilities do not automatically grant permissions |

## Current project status

<div align="center">
  <h3>EXPERIMENTAL FOUNDATION · GATEWAY ALPHA UNDER REVIEW</h3>
  <p><strong>Gateway implementation submitted · PR checks passing · independent security review pending</strong></p>
</div>

**Important release distinction:** the six-agent foundation and static directory are on `main`. The Local AI Gateway implementation is currently on the Draft [Pull Request #1](https://github.com/tasnimamin38/toolixa-agents/pull/1), branch `feature/python-local-ai-gateway`. It has passed Windows/Python 3.11 checks and the GitHub CI and dependency-audit workflows, but it has not yet been merged into `main` or deployed as a hosted backend.

| Area | Current state |
|---|---|
| Static Agent Directory | Deployed on Vercel |
| Python core contracts and safety primitives | Experimental foundation on `main` |
| Six bounded starter agents | Experimental on `main` |
| Local browser-based AI Gateway | Implemented on Draft PR #1 |
| OpenAI Chat Completions-compatible provider routing | Implemented on Draft PR #1 |
| Native vendor protocols and MCP tool execution | Planned — Phase 2 |
| Real multi-agent runtime and isolated execution | Planned — Phase 3 |
| Production hardening and hosted multi-user SaaS | Not started — later phases |

This is **not production-ready software**. The gateway is a single-user, loopback-only local alpha. Do not expose it to the public internet or use it as an unreviewed executor for untrusted code.

## What is included

<table>
  <tr>
    <td width="33%" valign="top">
      <h3>01 · Agent SDK</h3>
      Shared Python contracts, request/result models, execution budgets, provider and tool interfaces, policy checks and memory abstractions.
    </td>
    <td width="33%" valign="top">
      <h3>02 · Local AI Gateway</h3>
      Browser dashboard, encrypted local provider credentials, model discovery, chat playground and a compatible local API.
    </td>
    <td width="33%" valign="top">
      <h3>03 · Safety primitives</h3>
      Deny-by-default permissions, one-time approvals, secret redaction and a disabled-by-default process executor.
    </td>
  </tr>
  <tr>
    <td valign="top">
      <h3>04 · Starter agents</h3>
      Six separately documented Python agents with bounded, inspectable behavior.
    </td>
    <td valign="top">
      <h3>05 · Provider flexibility</h3>
      Connect any trusted upstream that implements the supported OpenAI Chat Completions-compatible API surface.
    </td>
    <td valign="top">
      <h3>06 · Quality gates</h3>
      Automated tests, Ruff, compile checks, catalog validation and dependency auditing in GitHub Actions.
    </td>
  </tr>
</table>

## Agent directory

| Agent | Current capability | Important boundary |
|---|---|---|
| **Dev Copilot** | Read-only Python workspace inspection and AST analysis | Does not execute or modify code |
| **Aegis Security** | Passive local secret-pattern and risky-code checks | Not an active scanner or penetration tester |
| **Task Orchestrator** | Deterministic task dependency ordering | Does not launch autonomous sub-agents |
| **RAG Chatbot** | Local Markdown/text retrieval with source line ranges | Lexical retrieval, not vector/embedding search |
| **Content Maestro** | Structured editorial brief and research checklist | Does not perform live web research |
| **Web Scraper** | Parse supplied local HTML into metadata, headings and links | No remote crawling or arbitrary HTTP fetching |

Browse the [live directory](https://toolixa-agents.vercel.app/) or inspect each agent under `agents/`.

## Architecture

The diagram shows the Local AI Gateway implemented on Draft PR #1. The six-agent foundation is on `main`; automatic agent-to-gateway wiring and the MCP tool bridge remain future integrations.

```mermaid
flowchart LR
    subgraph LOCAL["Your computer · Python runtime"]
      UI["Browser dashboard"]
      API["Toolixa Gateway API"]
      VAULT[("Encrypted local vault")]
      DB[("Local SQLite")]
      UI --> API
      API <--> DB
      DB --> VAULT
    end

    CLIENT["OpenAI-compatible client"] -->|"Bearer Toolixa key"| API
    API --> ROUTER["Provider HTTP adapter"]
    ROUTER --> MODEL["Your configured model endpoint"]

    AGENT["Six bounded starter agents"] -. "future model wiring" .-> API
    MCP["MCP servers and tools"] -. "Phase 2" .-> API
```

### Local gateway request flow

1. Start the gateway from PowerShell.
2. Open the local dashboard in your browser.
3. Add a provider name, API base URL and provider credential.
4. Test the connection and discover available models.
5. Use the playground or create a Toolixa API key.
6. Connect a compatible client to the local `/v1` endpoint.

## Provider compatibility

The Local AI Gateway adapter on Draft PR #1 supports the **OpenAI Chat Completions-compatible** model listing, JSON chat and streaming chat surface. This is a compatibility boundary, not a claim that every vendor-native API is already implemented.

| Provider or runtime | Connection approach |
|---|---|
| OpenRouter | OpenAI-compatible API endpoint |
| Ollama | Its OpenAI-compatible local endpoint |
| LM Studio | Its local OpenAI-compatible server |
| vLLM | Its OpenAI-compatible server |
| Other gateways and hosted/local models | Any trusted endpoint implementing the supported routes |
| Native Anthropic / Gemini APIs | Planned dedicated adapters |
| MCP servers | Planned Python MCP client and permission-aware tool bridge |

See [Provider and Gateway setup](https://github.com/tasnimamin38/toolixa-agents/blob/feature/python-local-ai-gateway/docs/gateway-guide.md) for endpoint requirements and limitations.

## Quick start

### 1. Install the core SDK

Requirements: Python 3.11+ and Git.

```powershell
git clone https://github.com/tasnimamin38/toolixa-agents.git
cd toolixa-agents

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e ./core
```

### 2. Run a bounded starter agent

For example, the read-only Dev Copilot:

```powershell
cd agents/01-dev-copilot
python main.py --workspace C:\path\to\your\project
```

Each agent has its own README, manifest and dependency file. Review its exact scope before running it.

### 3. Run the Local AI Gateway

The gateway is currently available on [Draft PR #1](https://github.com/tasnimamin38/toolixa-agents/pull/1), not on the default `main` branch yet. To try that version, clone the feature branch:

```powershell
git clone --branch feature/python-local-ai-gateway https://github.com/tasnimamin38/toolixa-agents.git
cd toolixa-agents

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e ".\core[gateway]"
python -m toolixa_core.gateway
```

The terminal prints a one-time dashboard password. Open `http://127.0.0.1:20128` in your browser. The compatible API base is `http://127.0.0.1:20128/v1`.

The gateway binds to loopback only. **Do not port-forward, tunnel or reverse-proxy this experimental service to the public internet.**

## Security and credential handling

- Provider API keys are encrypted in the local SQLite store. The vault key is kept separately in the user's application-data directory.
- Toolixa API keys are displayed once and stored as hashes.
- The dashboard is protected by a local password and a signed session cookie.
- The local gateway rejects non-loopback plaintext HTTP endpoints and does not follow provider redirects.
- No real provider key or paid model request is required for installation or automated tests.
- The gateway has not yet completed an independent penetration test or full production web-security review.
- A configured provider receives the prompts and conversation data sent to it. Review that provider's privacy, retention and billing terms.

Read the [Security Model](docs/security-model.md) before connecting credentials or enabling any additional capabilities.

## Roadmap

| Phase | Objective | Status |
|---|---|---|
| **0 · Foundation** | Python core, six bounded starter agents, static directory, CI | <strong>Completed</strong> |
| **1 · Local Gateway** | Browser dashboard, encrypted BYOK store, compatible provider API | <strong>Implemented on Draft PR #1; review pending</strong> |
| **2 · Native AI + MCP** | Native provider adapters, MCP registration/discovery, permission-gated tool calls | Planned |
| **3 · Agent Runtime** | Per-agent model selection, multi-agent orchestration, persistent memory, isolated tools | Planned |
| **4 · Production Gate** | Threat-model review, penetration testing, rate limits, audit, egress and operational controls | Not started |
| **5 · Hosted Service** | Optional multi-user SaaS, tenant isolation, remote secrets, quotas and billing | Not started |

### When does Experimental end?

Experimental status does not end just because the dashboard or API exists. The project moves out of experimental only after the agents perform their documented jobs reliably, provider and MCP integrations pass adversarial testing, tool execution is isolated, credentials and tenants are protected, and an independent security review plus release acceptance tests are complete.

Until those conditions are met, the honest project status remains **Experimental**.

## Development and verification

For the current `main` foundation, install the core SDK and development tools:

```powershell
python -m pip install -e ./core
python -m pip install -r agents/06-web-scraper/requirements.txt
python -m pip install "pytest>=9.0.3,<10" "ruff>=0.8,<1"

python -m compileall -q core/src agents scripts tests
ruff check core/src agents scripts tests
ruff format --check core/src agents scripts tests
python scripts/build_catalog.py --check
python -m pytest -q
```

To run the Local AI Gateway preview, first check out the feature branch using the instructions above, then install `python -m pip install -e "./core[gateway]"`. Gateway contract tests use mocked upstream responses and do not make paid provider calls.

## Documentation

| Document | What it covers |
|---|---|
| [Architecture](docs/architecture.md) | Components, boundaries and data flow |
| [Security Model](docs/security-model.md) | Permissions, secrets, execution and threats |
| [Gateway Guide](https://github.com/tasnimamin38/toolixa-agents/blob/feature/python-local-ai-gateway/docs/gateway-guide.md) | Local dashboard, providers and compatible API (Draft PR #1) |
| [BYOR / BYOK Guide](docs/byor-guide.md) | Runtime and credentials ownership |
| [Installation](docs/installation.md) | Install and launch |
| [Development](docs/development.md) | Tests, lint, CI and contribution workflow |
| [Implementation Plan](docs/plans/2026-11-27-toolixa-agents-implementation.md) | Phase-by-phase acceptance gates |

## License

No license has been selected. Public visibility on GitHub does not grant permission to reuse, modify or redistribute this project. Do not assume an open-source license applies.

---

<div align="center">
  <strong>Toolixa Agents</strong><br/>
  <sub>Local-first · Python-first · Your models · Your runtime · Your control</sub><br/><br/>
  <a href="https://github.com/tasnimamin38/toolixa-agents">Repository</a> ·
  <a href="https://toolixa-agents.vercel.app/">Agent Directory</a> ·
  <a href="https://github.com/tasnimamin38/toolixa-agents/pulls">Pull requests</a>
</div>
