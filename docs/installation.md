# Installation Guide

## Requirements

- Python 3.11 or newer.
- Git.
- A virtual environment is strongly recommended.

The public Toolixa directory website is static and does not need to run locally. The local AI Gateway is a separate Python process.

## Clone and prepare

~~~powershell
git clone https://github.com/tasnimamin38/toolixa-agents.git
cd toolixa-agents
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ./core
~~~

On macOS or Linux, activate with `source .venv/bin/activate`.

## Run the local AI Gateway

Install the optional gateway extra. This adds FastAPI, Uvicorn, HTTPX, Jinja2 and cryptography without making them mandatory dependencies of the small core SDK.

~~~powershell
python -m pip install -e "./core[gateway]"
python -m toolixa_core.gateway
~~~

The first run prints a random one-time dashboard password and starts a server bound to `127.0.0.1:20128`. The browser opens automatically. Otherwise visit `http://127.0.0.1:20128`. The API base is `http://127.0.0.1:20128/v1`.

Use `python -m toolixa_core.gateway --help` for local options. `--port 20129` chooses another local port; `--no-open` prevents opening the browser.

Never expose this experimental dashboard/API through a public reverse proxy, tunnel, or port-forward. It is not a hosted or multi-user gateway.

## Add an upstream provider

Sign in to the local dashboard, add a provider's name, OpenAI Chat Completions-compatible API base URL and provider key, then select **Test connection** to discover models. Any provider exposing the compatible `GET /models` and `POST /chat/completions` contract can be used. Examples and API usage are in [the gateway guide](gateway-guide.md).

Provider secrets are encrypted in a local SQLite store; the encryption key is kept separately under the user's local application-data directory. Toolixa client keys are shown once and stored as hashes. Never add real credentials to `agent.json`, source code, README files, catalog data, logs, or Git.

## Install one agent

Install only the selected agent's requirements. For example, Web Scraper:

~~~powershell
python -m pip install -r agents/06-web-scraper/requirements.txt
~~~

Other initial agents use only the Python standard library plus toolixa-core.

Run an agent from its directory:

~~~powershell
cd agents/06-web-scraper
python main.py --help
~~~

The starter agents are still bounded experimental examples. The current gateway does not yet automatically attach model providers to every agent.

## Verify installation

From repository root:

~~~powershell
python scripts/build_catalog.py --check
python -m compileall -q core/src agents scripts tests
python -m pytest -q
~~~

## Standalone distribution

An agent folder depends on the compatible toolixa-core package unless its README explicitly says otherwise. Do not distribute a copied folder as a standalone bundle until its core dependency is pinned or included and installation has been tested in a clean virtual environment.
