# Toolixa Agent Ecosystem Implementation Plan

**Implementation status:** First foundation release implemented and verified on 2026-11-27.

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox syntax for tracking.

**Goal:** Deliver a static agent directory and a secure, modular Python starter ecosystem with six independently documented agents.

**Architecture:** A lightweight installable toolixa-core package defines provider-neutral contracts, policy checks, approvals, tool registration, memory interfaces, and a disabled-by-default executor. Six independent agent folders consume those interfaces; a generated manifest catalog feeds a static Vercel website.

**Tech Stack:** Python 3.11+, setuptools, pytest, Ruff, BeautifulSoup for local HTML parsing, vanilla HTML/CSS/JavaScript, GitHub Actions, Vercel static deployment.

## Global Constraints

- BYOR and BYOK remain separate.
- No hosted model runtime, database, billing system, or paid API is required.
- Core has no mandatory third-party runtime dependency.
- Agent-specific dependencies remain isolated.
- Shell execution and active security scanning are disabled by default.
- Manifests declare requested capabilities but never grant permissions.
- Scraping begins with supplied local HTML; network fetching is not enabled until an address-pinned transport or enforced egress boundary is implemented and tested.
- No license file or license claim is introduced.
- Canonical repository name is toolixa-agents.

---

### Task 1: Shared SDK and governance baseline

**Files:** core/pyproject.toml, core/src/toolixa_core/**, tests/core/test_core.py, docs/architecture.md, docs/security-model.md, docs/byor-guide.md, docs/plans/2026-11-27-toolixa-agents-implementation.md, README.md, pyproject.toml, .gitignore.

**Interfaces:** Produces AgentRequest, AgentResult, ExecutionBudget, AgentManifest, ProviderRegistry, ToolRegistry, RuntimePolicy, ApprovalManager, BudgetTracker, DisabledExecutor, ToolSpec, ToolCallContext, DocumentChunk, and ToolixaSettings.

- [x] Add and run tests for serialization, invalid budgets, artifact traversal, denied permissions, workspace boundaries, host allowlists, one-use approvals, step limits, provider selection, disabled execution, tool permission gates, and secret redaction.
- [x] Run: python -m pip install -e ./core && python -m pytest tests/core -q
- Expected: all focused core tests pass.
- [x] Run: python -m compileall -q core/src
- Expected: no syntax errors.
- [x] Commit: feat: establish Toolixa shared core and safety contracts.

### Task 2: Six independent agent starters

**Files:** agents/01-dev-copilot/**, agents/02-aegis-security/**, agents/03-task-orchestrator/**, agents/04-rag-chatbot/**, agents/05-content-maestro/**, agents/06-web-scraper/**, tests/agents/test_agent_starters.py, scripts/build_catalog.py, catalog/agents.json.

**Interfaces:** Produces read-only workspace analysis, passive local security findings, deterministic task dependency ordering, local text retrieval with source ranges, evidence-aware content briefs, and local HTML extraction.

- [x] Test all six agent behaviors with temporary local fixtures; no test may contact arbitrary external hosts or execute shell commands.
- [x] Run: python -m pytest tests/agents -q
- Expected: all six focused tests pass, secrets are not returned in findings, DAG cycles are rejected, RAG results cite line ranges, and scraper parses supplied HTML only.
- [x] Run: python scripts/build_catalog.py --check
- Expected: six manifests validate and generated catalog matches committed output.
- [x] Commit: feat: add six modular Toolixa agent starters.

### Task 3: Static Agent Directory

**Files:** index.html, assets/styles.css, assets/app.js, catalog/agents.json, vercel.json.

**Interfaces:** Consumes the deterministic catalog and produces a responsive static directory with search, category filters, status labels, and GitHub source/documentation links.

- [x] Verify catalog IDs and paths before rendering.
- [x] Use DOM text nodes and createElement; never inject catalog values with innerHTML.
- [x] Run: python scripts/build_catalog.py --check && python -m pytest -q
- Expected: deterministic catalog and all tests pass.
- [x] Verify Vercel config contains static headers only and no Python runtime or function.
- [x] Commit: feat: publish static Toolixa agent directory.

### Task 4: CI and release hygiene

**Files:** .github/workflows/ci.yml, .github/workflows/security.yml, docs/installation.md, docs/development.md.

**Interfaces:** Consumes core, manifests, agent tests, catalog, and static assets; produces repeatable pull-request quality and dependency-audit checks.

- [x] Run: python -m compileall -q core/src agents scripts tests
- Expected: no syntax errors.
- [x] Run: ruff check core/src agents scripts tests
- Expected: no lint findings.
- [x] Run: ruff format --check core/src agents scripts tests
- Expected: all tracked Python files are formatted.
- [x] Run: python scripts/build_catalog.py --check && python -m pytest -q
- Expected: all local checks pass.
- [x] Ensure CI does not require paid provider keys or perform uncontrolled scans.
- [x] Commit: ci: add Toolixa quality and dependency security checks.

## Completion criteria

- Exactly six validated agent manifests generate the catalog.
- Core installs and its contract/policy tests pass.
- Each agent runs its documented local starter behavior.
- The default executor always denies shell execution.
- Ungranted permissions and paths outside approved roots are denied.
- The first Web Scraper performs local HTML parsing only.
- The static directory uses safe DOM APIs and loads the generated catalog.
- CI covers tests, lint, compile, catalog consistency, and dependency auditing.
- Vercel remains static-only.
- No license file or license claim is introduced.


---

## Phase 1: Local AI Gateway (experimental alpha)

**Implementation status:** Local code and Windows/Python 3.11 validation complete on branch `feature/python-local-ai-gateway`; GitHub Actions CI and dependency audit passed for commit `00d3c4b3b8c3000f1d9531ffc210ff07337c090c`. Independent security review remains pending.

**Goal:** Turn Toolixa from a catalog plus SDK skeleton into a locally operated, browser-configurable AI gateway without making core SDK dependencies mandatory or introducing a hosted/paid runtime.

**Files:** `core/src/toolixa_core/gateway/**`, `core/pyproject.toml`, `tests/test_gateway_contract.py`, `.github/workflows/ci.yml`, `.github/workflows/security.yml`, `README.md`, `docs/gateway-guide.md`, `docs/installation.md`, `docs/byor-guide.md`, `docs/architecture.md`, `docs/security-model.md`.

**Interfaces:** Local Python CLI, server-rendered dashboard on loopback, encrypted local provider credentials, Toolixa-issued API keys, provider model discovery, OpenAI-compatible `/v1/models` and `/v1/chat/completions` JSON/SSE routes.

- [x] Keep `toolixa-core` base dependencies empty and make gateway dependencies an optional `[gateway]` extra.
- [x] Implement first-run local dashboard password, hash-based password check, local session cookie and trusted-host guard.
- [x] Implement Fernet-encrypted local provider-key storage and hash-only Toolixa API-key storage.
- [x] Implement configurable OpenAI Chat Completions-compatible endpoints and namespaced `provider/model` IDs.
- [x] Implement provider model discovery, non-streaming chat, streaming pass-through, dashboard playground and key revocation.
- [x] Add mock-only tests for storage, auth, endpoint validation, model listing, JSON/SSE chat, redaction and host validation; no live provider key or paid provider request is used.
- [x] Run on Windows Python 3.11.9: `pip install -e "./core[gateway]"`, compileall, Ruff check/format, catalog check and full pytest suite.
- [x] Local result: 36 tests passed; Ruff clean; all 49 Python files formatted; compile and catalog checks passed.
- [x] Push branch and verify GitHub Actions CI and dependency audit on commit `00d3c4b3b8c3000f1d9531ffc210ff07337c090c`; both workflows passed.
- [ ] Complete independent code/security review before any public release.

### Explicit limits of this phase

This phase supports the OpenAI Chat Completions-compatible API contract. It does not yet mean every proprietary provider protocol is supported. Native Anthropic/Gemini adapters, OAuth, MCP client/server and tool invocation, real per-agent model wiring, multi-agent orchestration, browser automation, isolated executor, remote multi-user access and production hardening remain future phases. The gateway is local-only and experimental; do not expose it publicly.

## Phase 2: Native provider protocols and MCP

- [ ] Add native protocol adapters (including Anthropic and Gemini) behind a shared model interface.
- [ ] Add provider capability metadata, model capabilities, health checks, timeouts, bounded retries and explicit fallback policy.
- [ ] Add the official Python MCP SDK as an optional integration extra.
- [ ] Implement MCP server registration over stdio and Streamable HTTP with explicit trust/allowlist configuration.
- [ ] Discover MCP tools/resources/prompts without automatically granting permission to call them.
- [ ] Add a permission-aware tool bridge; require per-tool/user approval for consequential actions and record redacted audit events.
- [ ] Test tool schema validation, malformed responses, server loss, timeouts, prompt injection, permission denial and secret redaction using fake MCP servers.

## Phase 3: Agent Runtime and memory

- [ ] Wire provider selection and Toolixa gateway clients into the six agent starters.
- [ ] Add per-agent and per-task model/tool policies, context limits, token budgets, cancellation and traceable execution state.
- [ ] Build isolated execution adapters only after a documented sandbox boundary exists; keep process execution disabled by default.
- [ ] Add source-aware persistent memory with explicit read/write permission and a replaceable vector-store interface.
- [ ] Add browser automation through an isolated, operator-approved browser runtime.
- [ ] Add multi-agent orchestration with dependency control, message provenance, cycle/depth limits and cancellation propagation.

## Phase 4: Production hardening gate

- [ ] Complete a documented threat-model review and independent penetration test.
- [ ] Add CSRF protection, session rotation/revocation, login throttling, API rate/size limits, request quotas and abuse controls.
- [ ] Add durable audit logs with tamper evidence, safe tracing/metrics and key-rotation/recovery procedures.
- [ ] Harden outbound networking with DNS/IP pinning or enforced egress control, redirect revalidation and private/metadata IP rejection.
- [ ] Add SBOM, signed releases, provenance, dependency pinning and continuous vulnerability response.
- [ ] Add backup/restore, deployment/runbook, incident-response and service-health acceptance tests.
- [ ] Do not market as production-ready until every mandatory gate has objective evidence.

## Phase 5: Optional hosted multi-user service

- [ ] Design identity, tenant isolation, remote secret storage/KMS, access control, quotas, billing and deletion/export workflows.
- [ ] Separate local-only gateway from hosted control plane and tenant data planes.
- [ ] Complete architecture, privacy and security reviews before enabling public signup or remote API access.
