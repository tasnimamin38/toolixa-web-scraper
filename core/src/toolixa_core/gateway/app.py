"""Local browser dashboard and OpenAI-compatible Toolixa API gateway."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, quote

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.trustedhost import TrustedHostMiddleware

from toolixa_core.gateway.providers import ProviderHTTPClient, ProviderHTTPError
from toolixa_core.gateway.security import issue_session, verify_session
from toolixa_core.gateway.store import GatewayStore, ProviderRecord

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_STATIC_DIR = Path(__file__).parent / "static"


def _form(body: bytes) -> dict[str, str]:
    parsed = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)
    return {key: values[-1] for key, values in parsed.items() if values}


def _parse_models(value: str) -> list[str]:
    return [item.strip() for item in value.replace("\n", ",").split(",") if item.strip()]


def _gateway_auth(store: GatewayStore, request: Request) -> bool:
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    return scheme.lower() == "bearer" and store.authenticate_api_key(token.strip())


def _model_route(store: GatewayStore, model: str) -> tuple[ProviderRecord, str] | None:
    provider_id, separator, upstream_model = model.partition("/")
    if not separator or not upstream_model:
        return None
    provider = store.get_provider(provider_id)
    if provider is None or upstream_model not in provider.models:
        return None
    return provider, upstream_model


def create_app(
    *, store: GatewayStore, provider_client: ProviderHTTPClient | None = None
) -> FastAPI:
    app = FastAPI(title="Toolixa Local AI Gateway", docs_url=None, redoc_url=None)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "localhost.localdomain", "testserver"],
    )
    app.state.store = store
    app.state.provider_client = provider_client or ProviderHTTPClient()
    templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; img-src 'self' data:; "
            "form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
        )
        return response

    def dashboard_context(request: Request, **extra):
        return {
            "request": request,
            "providers": store.list_providers(),
            "api_keys": store.list_api_keys(),
            "message": extra.get("message", ""),
            "new_api_key": extra.get("new_api_key", ""),
            "error": extra.get("error", ""),
            "model_choices": [
                {"id": f"{provider.id}/{model}"}
                for provider in store.list_providers()
                for model in provider.models
            ],
            "chat_result": extra.get("chat_result", ""),
            "chat_model": extra.get("chat_model", ""),
        }

    def logged_in(request: Request) -> bool:
        return verify_session(store.vault, request.cookies.get("toolixa_session"))

    @app.get("/healthz")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "toolixa-local-gateway"}

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        if logged_in(request):
            return RedirectResponse("/", status_code=303)
        return templates.TemplateResponse(
            request=request, name="login.html", context={"request": request, "error": ""}
        )

    @app.post("/login")
    async def login(request: Request):
        form = _form(await request.body())
        if not store.verify_admin_password(form.get("password", "")):
            return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={"request": request, "error": "Password did not match."},
                status_code=401,
            )
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(
            "toolixa_session",
            issue_session(store.vault),
            max_age=43_200,
            httponly=True,
            secure=False,
            samesite="strict",
            path="/",
        )
        return response

    @app.post("/logout")
    async def logout():
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie("toolixa_session", path="/")
        return response

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request, message: str = ""):
        if not logged_in(request):
            return RedirectResponse("/login", status_code=303)
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context=dashboard_context(request, message=message),
        )

    @app.post("/providers/add")
    async def add_provider(request: Request):
        if not logged_in(request):
            return RedirectResponse("/login", status_code=303)
        form = _form(await request.body())
        try:
            provider = store.add_provider(
                name=form.get("name", ""),
                base_url=form.get("base_url", ""),
                api_key=form.get("api_key", ""),
                models=_parse_models(form.get("models", "")),
            )
        except (ValueError, KeyError) as exc:
            return templates.TemplateResponse(
                request=request,
                name="dashboard.html",
                context=dashboard_context(request, error=str(exc)),
                status_code=400,
            )
        return RedirectResponse(
            f"/?message={quote(f'Provider {provider.name} was added. Run Test connection to discover models.')}#providers",
            status_code=303,
        )

    @app.post("/providers/{provider_id}/test")
    async def test_provider(request: Request, provider_id: str):
        if not logged_in(request):
            return RedirectResponse("/login", status_code=303)
        provider = store.get_provider(provider_id)
        if provider is None:
            return RedirectResponse("/?message=Provider%20not%20found#providers", status_code=303)
        try:
            models = await app.state.provider_client.list_models(
                provider, store.get_provider_secret(provider_id)
            )
            store.update_provider_models(provider_id, models)
            message = (
                f"Connection succeeded. Discovered {len(models)} model(s) for {provider.name}."
            )
        except (ProviderHTTPError, ValueError) as exc:
            message = f"Connection failed for {provider.name}: {str(exc)[:200]}"
        return RedirectResponse(f"/?message={quote(message)}#providers", status_code=303)

    @app.post("/providers/{provider_id}/delete")
    async def delete_provider(request: Request, provider_id: str):
        if not logged_in(request):
            return RedirectResponse("/login", status_code=303)
        deleted = store.delete_provider(provider_id)
        message = "Provider removed." if deleted else "Provider was not found."
        return RedirectResponse(f"/?message={quote(message)}#providers", status_code=303)

    @app.post("/keys/add")
    async def create_key(request: Request):
        if not logged_in(request):
            return RedirectResponse("/login", status_code=303)
        form = _form(await request.body())
        try:
            token = store.create_api_key(form.get("name", ""))
        except ValueError as exc:
            return templates.TemplateResponse(
                request=request,
                name="dashboard.html",
                context=dashboard_context(request, error=str(exc)),
                status_code=400,
            )
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context=dashboard_context(
                request,
                message="Copy this gateway key now. It will not be shown again.",
                new_api_key=token,
            ),
        )

    @app.post("/keys/{key_id}/revoke")
    async def revoke_key(request: Request, key_id: str):
        if not logged_in(request):
            return RedirectResponse("/login", status_code=303)
        store.revoke_api_key(key_id)
        return RedirectResponse("/?message=API%20key%20revoked#keys", status_code=303)

    @app.post("/playground")
    async def playground(request: Request):
        if not logged_in(request):
            return RedirectResponse("/login", status_code=303)
        form = _form(await request.body())
        model_name = form.get("model", "")
        prompt = form.get("prompt", "").strip()
        model_route = _model_route(store, model_name)
        if not prompt or len(prompt) > 20_000 or model_route is None:
            return templates.TemplateResponse(
                request=request,
                name="dashboard.html",
                context=dashboard_context(
                    request,
                    error="Choose an available model and enter a prompt of 1 to 20,000 characters.",
                    chat_model=model_name,
                ),
                status_code=400,
            )
        provider, upstream_model = model_route
        try:
            result = await app.state.provider_client.chat_completion(
                provider,
                store.get_provider_secret(provider.id),
                upstream_model,
                {"messages": [{"role": "user", "content": prompt}], "temperature": 0.2},
            )
            choices = result.get("choices", [])
            message = (
                choices[0].get("message", {}) if choices and isinstance(choices[0], dict) else {}
            )
            chat_result = str(message.get("content", "No text content returned."))
            error = ""
        except (ProviderHTTPError, KeyError, ValueError) as exc:
            chat_result = ""
            error = f"Model test failed: {str(exc)[:250]}"
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context=dashboard_context(
                request, chat_result=chat_result, chat_model=model_name, error=error
            ),
        )

    @app.post("/account/password")
    async def change_password(request: Request):
        if not logged_in(request):
            return RedirectResponse("/login", status_code=303)
        form = _form(await request.body())
        current = form.get("current_password", "")
        new = form.get("new_password", "")
        if not store.verify_admin_password(current):
            message = "Current password did not match."
        else:
            try:
                store.set_admin_password(new)
                message = "Dashboard password updated. Sign in again with the new password."
                response = RedirectResponse(f"/?message={quote(message)}", status_code=303)
                response.delete_cookie("toolixa_session", path="/")
                return response
            except ValueError as exc:
                message = str(exc)
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context=dashboard_context(request, error=message),
            status_code=400,
        )

    @app.get("/v1/models")
    async def list_gateway_models(request: Request):
        if not _gateway_auth(store, request):
            return JSONResponse(
                {
                    "error": {
                        "message": "A valid Toolixa gateway API key is required.",
                        "type": "authentication_error",
                    }
                },
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        data = []
        for provider in store.list_providers():
            for model in provider.models:
                data.append(
                    {"id": f"{provider.id}/{model}", "object": "model", "owned_by": provider.id}
                )
        return {"object": "list", "data": data}

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request):
        if not _gateway_auth(store, request):
            return JSONResponse(
                {
                    "error": {
                        "message": "A valid Toolixa gateway API key is required.",
                        "type": "authentication_error",
                    }
                },
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            payload = await request.json()
        except ValueError:
            return JSONResponse(
                {"error": {"message": "Request body must be valid JSON."}}, status_code=400
            )
        if not isinstance(payload, dict) or not isinstance(payload.get("messages"), list):
            return JSONResponse(
                {"error": {"message": "Request must contain a messages array."}}, status_code=422
            )
        model_route = _model_route(store, str(payload.get("model", "")))
        if model_route is None:
            return JSONResponse(
                {"error": {"message": "Model not found. Choose a model from GET /v1/models."}},
                status_code=404,
            )
        provider, upstream_model = model_route
        try:
            api_key = store.get_provider_secret(provider.id)
            if payload.get("stream") is True:
                upstream_client, upstream_response = await app.state.provider_client.open_stream(
                    provider, api_key, upstream_model, payload
                )
                if upstream_response.is_error:
                    await upstream_response.aread()
                    error_response = JSONResponse(
                        {
                            "error": {
                                "message": app.state.provider_client.error_message(
                                    upstream_response, api_key
                                )
                            }
                        },
                        status_code=upstream_response.status_code,
                    )
                    await upstream_response.aclose()
                    await upstream_client.aclose()
                    return error_response

                async def forward_stream():
                    secret_bytes = api_key.encode("utf-8") if api_key else b""
                    pending = b""
                    try:
                        async for chunk in upstream_response.aiter_bytes():
                            if not secret_bytes:
                                yield chunk
                                continue
                            combined = pending + chunk
                            overlap = 0
                            for candidate in range(
                                min(len(secret_bytes) - 1, len(combined)), 0, -1
                            ):
                                if combined.endswith(secret_bytes[:candidate]):
                                    overlap = candidate
                                    break
                            cutoff = len(combined) - overlap
                            safe_part = combined[:cutoff].replace(secret_bytes, b"[REDACTED]")
                            pending = combined[cutoff:]
                            if safe_part:
                                yield safe_part
                        if pending:
                            yield pending.replace(secret_bytes, b"[REDACTED]")
                    finally:
                        await upstream_response.aclose()
                        await upstream_client.aclose()

                media_type = upstream_response.headers.get("content-type", "text/event-stream")
                return StreamingResponse(
                    forward_stream(),
                    status_code=upstream_response.status_code,
                    media_type=media_type,
                )

            result = await app.state.provider_client.chat_completion(
                provider, api_key, upstream_model, payload
            )
        except ProviderHTTPError as exc:
            return JSONResponse(
                {"error": {"message": str(exc), "type": "upstream_error"}},
                status_code=exc.status_code,
            )
        except (KeyError, ValueError):
            return JSONResponse(
                {"error": {"message": "Provider configuration is unavailable."}}, status_code=502
            )
        return JSONResponse(result)

    return app
