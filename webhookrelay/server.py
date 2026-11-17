import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from . import signer, storage


class SignRequest(BaseModel):
    provider: str
    secret: str
    payload: str


class ReplayRequest(BaseModel):
    event_id: Optional[str] = None
    target_url: str
    method: str = "POST"
    provider: Optional[str] = None
    secret: Optional[str] = None
    payload: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


def create_app(
    db_path: str = "webhooks.db",
    forward_url: Optional[str] = None,
    default_secret: Optional[str] = None,
    default_provider: Optional[str] = None,
) -> FastAPI:
    storage.init_db(db_path)
    app = FastAPI(title="WebhookRelay Lite", docs_url=None, redoc_url=None)
    sse_subscribers: List[asyncio.Queue] = []

    static_dir = Path(__file__).parent / "static"
    dashboard_path = static_dir / "dashboard.html"

    @app.get("/", response_class=HTMLResponse)
    async def get_dashboard():
        if not dashboard_path.exists():
            raise HTTPException(status_code=404, detail="Dashboard UI file not found")
        return HTMLResponse(content=dashboard_path.read_text(encoding="utf-8"))

    @app.get("/api/events")
    async def api_list_events(limit: int = 100, search: Optional[str] = None):
        return storage.list_events(db_path, limit=limit, search=search)

    @app.get("/api/events/stream")
    async def api_events_stream():
        queue: asyncio.Queue = asyncio.Queue()
        sse_subscribers.append(queue)

        async def event_generator():
            try:
                while True:
                    data = await queue.get()
                    yield f"data: {json.dumps(data)}\n\n"
            except asyncio.CancelledError:
                pass
            finally:
                if queue in sse_subscribers:
                    sse_subscribers.remove(queue)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/api/events/{event_id}")
    async def api_get_event(event_id: str):
        ev = storage.get_event(db_path, event_id)
        if not ev:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
        return ev

    @app.delete("/api/events/{event_id}")
    async def api_delete_event(event_id: str):
        deleted = storage.delete_event(db_path, event_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
        return {"deleted": True, "id": event_id}

    @app.delete("/api/events")
    async def api_clear_events():
        count = storage.clear_events(db_path)
        return {"cleared": count}

    @app.post("/api/sign")
    async def api_sign(req: SignRequest):
        sig_headers = signer.sign_payload(req.provider, req.secret, req.payload)
        return {"headers": sig_headers}

    @app.post("/api/replay")
    async def api_replay(req: ReplayRequest):
        headers_to_send: Dict[str, str] = {}

        if req.event_id:
            orig = storage.get_event(db_path, req.event_id)
            if orig:
                for k, v in orig["headers"].items():
                    if k.lower() not in {"host", "content-length"}:
                        headers_to_send[k] = v

        if req.headers:
            headers_to_send.update(req.headers)

        payload_to_send = req.payload if req.payload is not None else ""
        provider_name = req.provider or default_provider
        secret_key = req.secret or default_secret

        if provider_name and secret_key:
            sig_headers = signer.sign_payload(provider_name, secret_key, payload_to_send)
            headers_to_send.update(sig_headers)

        if "content-type" not in {k.lower() for k in headers_to_send}:
            headers_to_send["Content-Type"] = "application/json"

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.request(
                    method=req.method.upper(),
                    url=req.target_url,
                    content=payload_to_send.encode("utf-8"),
                    headers=headers_to_send,
                )
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return {
                    "status_code": res.status_code,
                    "response_body": res.text,
                    "duration_ms": duration_ms,
                    "headers": dict(res.headers),
                }
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "status_code": 502,
                "response_body": f"Replay error: {str(e)}",
                "duration_ms": duration_ms,
                "headers": {},
            }

    @app.api_route(
        "/webhook{full_path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    )
    @app.api_route(
        "/events{full_path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    )
    async def ingest_webhook(request: Request, full_path: str = ""):
        body_bytes = await request.body()
        body_text = body_bytes.decode("utf-8", errors="replace")

        headers_dict = {k: v for k, v in request.headers.items()}
        query_dict = dict(request.query_params)
        client_ip = request.client.host if request.client else "127.0.0.1"
        content_type = request.headers.get("content-type", "application/json")

        path_recorded = request.url.path

        event = storage.save_event(
            db_path=db_path,
            method=request.method,
            path=path_recorded,
            headers=headers_dict,
            query_params=query_dict,
            client_ip=client_ip,
            content_type=content_type,
            body=body_text,
        )

        for q in list(sse_subscribers):
            try:
                q.put_nowait(event)
            except Exception:
                pass

        if forward_url:
            asyncio.create_task(
                _forward_event(forward_url, request.method, headers_dict, body_bytes)
            )

        return {
            "status": "received",
            "id": event["id"],
            "timestamp": event["created_at"],
        }

    return app


async def _forward_event(
    target_url: str, method: str, headers: Dict[str, str], body: bytes
) -> None:
    forward_headers = {
        k: v for k, v in headers.items() if k.lower() not in {"host", "content-length"}
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.request(
                method=method,
                url=target_url,
                content=body,
                headers=forward_headers,
            )
    except Exception:
        pass
