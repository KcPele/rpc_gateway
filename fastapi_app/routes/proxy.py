from __future__ import annotations

import random
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from fastapi_app.config.settings import settings
from fastapi_app.middleware.api_key import validate_api_key
from fastapi_app.middleware.rate_limit import rate_limit
from fastapi_app.services.metrics import record_rpc_metrics, record_rate_limit_hit

router = APIRouter(tags=["proxy"])

_keep_alive_limits = httpx.Limits(max_connections=128, max_keepalive_connections=32)
_async_client = httpx.AsyncClient(limits=_keep_alive_limits, timeout=60.0)


def _get_random_url(urls: list[str] | None) -> str | None:
    if not urls or len(urls) == 0:
        return None
    return random.choice(urls)


async def _proxy_request(
    request: Request,
    response: Response,
    target_url: str,
    chain_name: str,
    endpoint_type: str,
    app_doc: dict | None = None,
    api_key: str | None = None,
):
    url = target_url.rstrip("/") + request.url.path
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length", "transfer-encoding")
    }

    body = await request.body()

    start_time = datetime.now(timezone.utc)

    try:
        resp = await _async_client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
            params=request.query_params,
        )

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        response.headers["X-RPC-Gateway"] = "NodeBridge"
        response.headers["X-Endpoint-Type"] = f"{chain_name}-{endpoint_type}"
        response.headers["X-Response-Time"] = f"{duration}s"

        if app_doc and api_key:
            user_id = app_doc.get("user_id", "unknown")
            rpc_method = "unknown"
            try:
                import json

                req_body = json.loads(body)
                rpc_method = req_body.get("method", "unknown")
            except Exception:
                pass

            record_rpc_metrics(user_id, api_key, rpc_method, endpoint_type, duration)

        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers),
            media_type=resp.headers.get("content-type"),
        )

    except httpx.ConnectError as exc:
        return Response(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=(
                f'{{"error": "Bad Gateway", "message": "Failed to connect to the '
                f'{chain_name} {endpoint_type} node", "endpointType": "{chain_name}-{endpoint_type}"}}'
            ),
            media_type="application/json",
        )
    except Exception as exc:
        return Response(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=(
                f'{{"error": "Bad Gateway", "message": "{str(exc)}", '
                f'"endpointType": "{chain_name}-{endpoint_type}"}}'
            ),
            media_type="application/json",
        )


@router.api_route(
    "/{chain}/exec/{key}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy_execution(
    request: Request,
    response: Response,
):
    chain_name = request.path_params.get("chain", "").lower()
    key = request.path_params.get("key", "")
    path = request.path_params.get("path", "")

    chain_config = settings.get_chain_config(chain_name)
    if not chain_config or not chain_config.execution_rpc_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution RPC URL not configured for chain {chain_name}",
        )

    selected_url = _get_random_url(chain_config.execution_rpc_url)
    if not selected_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to select execution RPC URL for chain {chain_name}",
        )

    app_doc = await validate_api_key(request)
    request.state.app = app_doc

    await rate_limit(request, response)

    target_url = selected_url.rstrip("/") + "/" + path
    return await _proxy_request(
        request,
        response,
        target_url,
        chain_name,
        "execution",
        app_doc=app_doc,
        api_key=key,
    )


@router.api_route(
    "/{chain}/cons/{key}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy_consensus(
    request: Request,
    response: Response,
):
    chain_name = request.path_params.get("chain", "").lower()
    key = request.path_params.get("key", "")
    path = request.path_params.get("path", "")

    chain_config = settings.get_chain_config(chain_name)
    if not chain_config or not chain_config.consensus_api_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consensus API URL not configured for chain {chain_name}",
        )

    selected_url = _get_random_url(chain_config.consensus_api_url)
    if not selected_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to select consensus API URL for chain {chain_name}",
        )

    app_doc = await validate_api_key(request)
    request.state.app = app_doc

    await rate_limit(request, response)

    target_url = selected_url.rstrip("/") + "/" + path
    return await _proxy_request(
        request,
        response,
        target_url,
        chain_name,
        "consensus",
        app_doc=app_doc,
        api_key=key,
    )


@router.get("/health/{chain}")
async def check_proxy_health(chain: str):
    chain_name = chain.lower()
    chain_config = settings.get_chain_config(chain_name)

    if not chain_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration for chain '{chain_name}' not found.",
        )

    exec_urls = chain_config.execution_rpc_url or []
    cons_urls = chain_config.consensus_api_url or []

    if not exec_urls and not cons_urls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No RPC/API URLs configured for chain '{chain_name}'.",
        )

    health_checks: dict = {}

    selected_exec = _get_random_url(exec_urls) if exec_urls else None
    if selected_exec:
        health_checks["execution"] = {"url": selected_exec, "status": "unhealthy"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    selected_exec,
                    json={
                        "jsonrpc": "2.0",
                        "method": "eth_blockNumber",
                        "params": [],
                        "id": 1,
                    },
                    headers={"Content-Type": "application/json"},
                )
                health_checks["execution"]["status"] = (
                    "healthy" if resp.status_code == 200 else "unhealthy"
                )
        except Exception:
            health_checks["execution"]["status"] = "unhealthy"
    else:
        health_checks["execution"] = {"url": None, "status": "not_configured"}

    selected_cons = _get_random_url(cons_urls) if cons_urls else None
    if selected_cons:
        health_checks["consensus"] = {"url": selected_cons, "status": "unhealthy"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{selected_cons}/eth/v1/node/health")
                health_checks["consensus"]["status"] = (
                    "healthy" if resp.status_code == 200 else "unhealthy"
                )
        except Exception:
            health_checks["consensus"]["status"] = "unhealthy"
    else:
        health_checks["consensus"] = {"url": None, "status": "not_configured"}

    any_unhealthy = any(v.get("status") == "unhealthy" for v in health_checks.values())
    all_healthy_or_nc = all(
        v.get("status") in ("healthy", "not_configured") for v in health_checks.values()
    )

    if any_unhealthy:
        overall = "unhealthy"
    elif all_healthy_or_nc:
        overall = "healthy"
    else:
        overall = "not_configured"

    return {
        "status": overall,
        "chain": chain_name,
        "checks": health_checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
