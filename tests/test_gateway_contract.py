from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from toolixa_core.gateway.app import create_app
from toolixa_core.gateway.providers import ProviderHTTPClient
from toolixa_core.gateway.security import SecretVault, validate_base_url
from toolixa_core.gateway.store import GatewayStore


def make_store(tmp_path: Path) -> GatewayStore:
    vault = SecretVault.from_file(tmp_path / "vault.key")
    return GatewayStore(tmp_path / "gateway.sqlite3", vault)


def test_vault_encrypts_provider_key_and_store_never_lists_plaintext(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    record = store.add_provider(
        name="Local model",
        base_url="http://127.0.0.1:11434/v1",
        api_key="super-secret-provider-key",
        models=["qwen2.5:7b"],
    )

    raw_db = (tmp_path / "gateway.sqlite3").read_bytes()
    assert b"super-secret-provider-key" not in raw_db
    assert "super-secret-provider-key" not in repr(store.list_providers())
    assert store.get_provider_secret(record.id) == "super-secret-provider-key"


def test_gateway_keys_are_shown_once_and_only_hashes_are_persisted(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    token = store.create_api_key("desktop client")

    assert token.startswith("tla_")
    assert store.authenticate_api_key(token) is True
    assert store.authenticate_api_key(token + "wrong") is False
    assert token not in repr(store.list_api_keys())
    assert token.encode() not in (tmp_path / "gateway.sqlite3").read_bytes()


def test_base_url_requires_https_except_local_loopback() -> None:
    assert validate_base_url("https://api.example.com/v1") == "https://api.example.com/v1"
    assert validate_base_url("http://localhost:11434/v1") == "http://localhost:11434/v1"
    with pytest.raises(ValueError):
        validate_base_url("http://api.example.com/v1")
    with pytest.raises(ValueError):
        validate_base_url("https://user:pass@example.com/v1")


def test_gateway_api_lists_namespaced_models_and_proxies_chat(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.set_admin_password("test-dashboard-password")
    store.add_provider(
        name="Cloud provider",
        base_url="https://api.example.test/v1",
        api_key="upstream-secret",
        models=["test-chat-model"],
    )
    gateway_key = store.create_api_key("test integration")

    def upstream(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer upstream-secret"
        if request.url.path.endswith("/chat/completions"):
            body = json.loads(request.content)
            assert body["model"] == "test-chat-model"
            assert body["messages"] == [{"role": "user", "content": "hello"}]
            return httpx.Response(
                200,
                json={
                    "id": "chatcmpl-test",
                    "object": "chat.completion",
                    "choices": [
                        {"index": 0, "message": {"role": "assistant", "content": "hello back"}}
                    ],
                },
            )
        return httpx.Response(404, json={"error": "not found"})

    client = ProviderHTTPClient(transport=httpx.MockTransport(upstream))
    app = create_app(store=store, provider_client=client)
    with TestClient(app) as browser:
        unauthorized = browser.get("/v1/models")
        assert unauthorized.status_code == 401
        headers = {"Authorization": f"Bearer {gateway_key}"}
        models = browser.get("/v1/models", headers=headers)
        assert models.status_code == 200
        assert models.json()["data"][0]["id"] == "cloud-provider/test-chat-model"

        completion = browser.post(
            "/v1/chat/completions",
            headers=headers,
            json={
                "model": "cloud-provider/test-chat-model",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
        assert completion.status_code == 200
        assert completion.json()["choices"][0]["message"]["content"] == "hello back"


def test_dashboard_login_and_provider_add_never_echo_api_key(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.set_admin_password("correct horse battery staple")
    app = create_app(
        store=store,
        provider_client=ProviderHTTPClient(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"data": []}))
        ),
    )

    with TestClient(app, follow_redirects=False) as browser:
        assert browser.get("/").status_code in {302, 303}
        login = browser.post(
            "/login", data={"password": "correct horse battery staple"}, follow_redirects=True
        )
        assert login.status_code == 200
        response = browser.post(
            "/providers/add",
            data={
                "name": "Custom AI",
                "base_url": "https://custom.example.test/v1",
                "api_key": "must-not-be-rendered",
                "models": "alpha-model,beta-model",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert "Custom AI" in response.text
        assert "must-not-be-rendered" not in response.text
        assert "alpha-model" in response.text


def test_provider_discovery_and_revoked_gateway_key(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.set_admin_password("test-dashboard-password")
    store.add_provider(
        name="Discoverable",
        base_url="https://models.example.test/v1",
        api_key="discovery-secret",
        models=[],
    )
    gateway_key = store.create_api_key("temporary client")

    def upstream(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer discovery-secret"
        return httpx.Response(200, json={"data": [{"id": "model-x"}, {"id": "model-y"}]})

    app = create_app(
        store=store, provider_client=ProviderHTTPClient(transport=httpx.MockTransport(upstream))
    )
    with TestClient(app, follow_redirects=False) as browser:
        browser.post("/login", data={"password": "test-dashboard-password"})
        response = browser.post("/providers/discoverable/test")
        assert response.status_code == 303
        models = browser.get("/v1/models", headers={"Authorization": f"Bearer {gateway_key}"})
        assert [item["id"] for item in models.json()["data"]] == [
            "discoverable/model-x",
            "discoverable/model-y",
        ]

    key_id = store.list_api_keys()[0]["id"]
    assert store.revoke_api_key(str(key_id)) is True
    assert store.authenticate_api_key(gateway_key) is False


def test_provider_error_and_chat_output_redact_upstream_secret(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.add_provider(
        name="Echo provider",
        base_url="https://echo.example.test/v1",
        api_key="provider-secret-123456",
        models=["echo-model"],
    )
    gateway_key = store.create_api_key("redaction test")

    def upstream(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/chat/completions"):
            return httpx.Response(
                200, json={"choices": [{"message": {"content": "provider-secret-123456"}}]}
            )
        return httpx.Response(
            401, json={"error": {"message": "invalid key provider-secret-123456"}}
        )

    app = create_app(
        store=store, provider_client=ProviderHTTPClient(transport=httpx.MockTransport(upstream))
    )
    with TestClient(app) as browser:
        headers = {"Authorization": f"Bearer {gateway_key}"}
        completion = browser.post(
            "/v1/chat/completions",
            headers=headers,
            json={
                "model": "echo-provider/echo-model",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
        assert "provider-secret-123456" not in completion.text
        assert "[REDACTED]" in completion.text

        # A discovery error must also remove any echoed credential.
        provider = store.get_provider("echo-provider")
        from toolixa_core.gateway.providers import ProviderHTTPError

        with pytest.raises(ProviderHTTPError, match=r"\[REDACTED\]"):
            browser.portal.call(
                app.state.provider_client.list_models, provider, "provider-secret-123456"
            )


def test_streaming_chat_completions_proxy(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.add_provider(
        name="Stream provider",
        base_url="https://stream.example.test/v1",
        api_key="stream-secret-123456",
        models=["stream-model"],
    )
    gateway_key = store.create_api_key("stream client")

    def upstream(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["stream"] is True
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=b'data: {"content":"hello"}\n\n',
        )

    app = create_app(
        store=store, provider_client=ProviderHTTPClient(transport=httpx.MockTransport(upstream))
    )
    with TestClient(app) as browser:
        response = browser.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {gateway_key}"},
            json={
                "model": "stream-provider/stream-model",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": True,
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert "hello" in response.text


def test_dashboard_playground_sends_prompt_to_selected_model(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.set_admin_password("test-dashboard-password")
    store.add_provider(
        name="Playground provider",
        base_url="https://playground.example.test/v1",
        api_key="playground-secret",
        models=["chat-model"],
    )

    def upstream(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["model"] == "chat-model"
        assert body["messages"][0]["content"] == "Say ready"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Ready."}}]},
        )

    app = create_app(
        store=store, provider_client=ProviderHTTPClient(transport=httpx.MockTransport(upstream))
    )
    with TestClient(app, follow_redirects=False) as browser:
        browser.post("/login", data={"password": "test-dashboard-password"})
        response = browser.post(
            "/playground",
            data={"model": "playground-provider/chat-model", "prompt": "Say ready"},
        )
        assert response.status_code == 200
        assert "Ready." in response.text
        assert "playground-secret" not in response.text


def test_provider_slug_collisions_get_distinct_ids(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    first = store.add_provider(
        name="Open AI", base_url="https://one.example.test/v1", models=["model-a"]
    )
    second = store.add_provider(
        name="Open-AI", base_url="https://two.example.test/v1", models=["model-b"]
    )
    assert first.id == "open-ai"
    assert second.id == "open-ai-2"


def test_stream_redacts_provider_secret_even_when_split_across_chunks(tmp_path: Path) -> None:
    class SplitSecretStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"data: prefix stream-secret-"
            yield b"123456 suffix\n\n"

    store = make_store(tmp_path)
    store.add_provider(
        name="Split stream provider",
        base_url="https://split.example.test/v1",
        api_key="stream-secret-123456",
        models=["split-model"],
    )
    token = store.create_api_key("split stream client")

    def upstream(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"content-type": "text/event-stream"}, stream=SplitSecretStream()
        )

    app = create_app(
        store=store, provider_client=ProviderHTTPClient(transport=httpx.MockTransport(upstream))
    )
    with TestClient(app) as browser:
        response = browser.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "model": "split-stream-provider/split-model",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": True,
            },
        )
        assert "stream-secret-123456" not in response.text
        assert "[REDACTED]" in response.text


def test_dashboard_rejects_untrusted_host_headers(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    app = create_app(store=store)
    with TestClient(app) as browser:
        response = browser.get("/healthz", headers={"Host": "attacker.example"})
        assert response.status_code == 400


def test_discovered_model_ids_redact_provider_credential(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    provider = store.add_provider(
        name="Model echo",
        base_url="https://models.example.test/v1",
        api_key="credential-model-secret",
    )

    def upstream(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"id": "credential-model-secret"}]})

    client = ProviderHTTPClient(transport=httpx.MockTransport(upstream))
    models = __import__("asyncio").run(client.list_models(provider, "credential-model-secret"))
    assert models == ["[REDACTED]"]
