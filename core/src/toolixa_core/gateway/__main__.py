"""Run the local Toolixa dashboard and OpenAI-compatible API gateway."""

from __future__ import annotations

import argparse
import os
import threading
import webbrowser
from pathlib import Path

import uvicorn

from toolixa_core.gateway.app import create_app
from toolixa_core.gateway.providers import ProviderHTTPClient
from toolixa_core.gateway.security import SecretVault
from toolixa_core.gateway.store import GatewayStore


def data_directory() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "Toolixa" / "gateway"
    return Path.home() / ".local" / "share" / "toolixa" / "gateway"


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the Toolixa local AI gateway dashboard")
    parser.add_argument("--port", type=int, default=20128)
    parser.add_argument(
        "--no-open", action="store_true", help="do not open the dashboard in a browser"
    )
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("--port must be between 1024 and 65535")

    directory = data_directory()
    vault = SecretVault.from_file(directory / "vault.key")
    store = GatewayStore(directory / "gateway.sqlite3", vault)
    bootstrap_password = store.create_admin_password_if_missing()
    url = f"http://127.0.0.1:{args.port}"
    print("Toolixa local AI gateway")
    print(f"Dashboard: {url}")
    print(f"OpenAI-compatible API base: {url}/v1")
    print(f"Local data directory: {directory}")
    if bootstrap_password:
        print("\nFIRST-RUN DASHBOARD PASSWORD (save it now; it will not be shown again):")
        print(bootstrap_password)
    else:
        print("Dashboard password: use the password you previously set.")
    print(
        "\nThis server binds to 127.0.0.1 only. Do not expose it directly to the public internet."
    )
    if not args.no_open:
        threading.Timer(1.2, webbrowser.open, args=(url,)).start()
    app = create_app(store=store, provider_client=ProviderHTTPClient())
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
