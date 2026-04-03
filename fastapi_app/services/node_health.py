from __future__ import annotations

import httpx
from fastapi import HTTPException, status

from fastapi_app.config.settings import settings


def _extract_metric(metrics_text: str, metric_name: str) -> str:
    """Extract a metric value from Prometheus text format."""
    for line in metrics_text.split("\n"):
        if not line.startswith("#") and metric_name in line:
            parts = line.split()
            if len(parts) >= 2 and parts[0] == metric_name:
                return parts[1]
    return "not_found"


async def check_execution_nodes(exec_urls: list[str]) -> list[dict]:
    """Check health of execution layer nodes."""
    results = []
    for url in exec_urls:
        try:
            async with httpx.AsyncClient(timeout=50.0) as client:
                resp = await client.post(
                    url,
                    json={
                        "jsonrpc": "2.0",
                        "method": "eth_syncing",
                        "params": [],
                        "id": 1,
                    },
                )
                data = resp.json()
                result = data.get("result")
                results.append(
                    {
                        "nodeIndex": len(results),
                        "nodeUrl": url,
                        "status": "available",
                        "syncing": result
                        if result is not None and result is not False
                        else (result is False),
                        "error": None,
                    }
                )
        except Exception as exc:
            results.append(
                {
                    "nodeIndex": len(results),
                    "nodeUrl": url,
                    "status": "unavailable",
                    "syncing": "unknown",
                    "error": str(exc),
                }
            )
    return results


async def check_consensus_nodes(cons_urls: list[str]) -> list[dict]:
    """Check health of consensus layer nodes."""
    results = []
    for url in cons_urls:
        try:
            async with httpx.AsyncClient(timeout=50.0) as client:
                resp = await client.get(f"{url}/eth/v1/node/syncing")
                data = resp.json().get("data", {})
                results.append(
                    {
                        "nodeIndex": len(results),
                        "nodeUrl": url,
                        "status": "available",
                        "syncing": data.get("is_syncing", "unknown"),
                        "head_slot": data.get("head_slot", "unknown"),
                        "error": None,
                    }
                )
        except Exception as exc:
            results.append(
                {
                    "nodeIndex": len(results),
                    "nodeUrl": url,
                    "status": "unavailable",
                    "syncing": "unknown",
                    "head_slot": "unknown",
                    "error": str(exc),
                }
            )
    return results


async def check_prometheus_nodes(prom_urls: list[str]) -> list[dict]:
    """Check availability of Prometheus metrics endpoints."""
    results = []
    for url in prom_urls:
        try:
            async with httpx.AsyncClient(timeout=50.0) as client:
                await client.get(f"{url}/metrics")
                results.append(
                    {
                        "nodeIndex": len(results),
                        "nodeUrl": url,
                        "status": "available",
                        "error": None,
                    }
                )
        except Exception as exc:
            results.append(
                {
                    "nodeIndex": len(results),
                    "nodeUrl": url,
                    "status": "unavailable",
                    "error": str(exc),
                }
            )
    return results


def compute_overall_health(
    exec_urls: list[str],
    cons_urls: list[str],
    prom_urls: list[str],
    exec_results: list[dict],
    cons_results: list[dict],
    prom_results: list[dict],
) -> str:
    """Compute overall node health status."""
    exec_status = (
        "healthy"
        if any(n["status"] == "available" for n in exec_results)
        else "unhealthy"
        if exec_urls
        else "not_configured"
    )
    cons_status = (
        "healthy"
        if any(n["status"] == "available" for n in cons_results)
        else "unhealthy"
        if cons_urls
        else "not_configured"
    )
    metrics_status = (
        "available"
        if any(n["status"] == "available" for n in prom_results)
        else "unavailable"
        if prom_urls
        else "not_configured"
    )

    unhealthy_count = [exec_status, cons_status].count("unhealthy")
    if prom_urls and metrics_status == "unavailable":
        unhealthy_count += 1

    not_configured_count = sum([not exec_urls, not cons_urls, not prom_urls])

    if unhealthy_count == 0:
        overall = "healthy"
    elif unhealthy_count == 1 and unhealthy_count + not_configured_count < 2:
        overall = "degraded"
    else:
        overall = "unhealthy"

    if not exec_urls and not cons_urls:
        overall = "not_configured"

    return overall


async def collect_node_metrics(chain_name: str) -> dict:
    """Collect detailed metrics from Prometheus endpoints."""
    chain_config = settings.get_chain_config(chain_name)
    if not chain_config or not chain_config.prometheus_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prometheus URL not configured for chain: {chain_name}",
        )

    prom_urls = chain_config.prometheus_url
    node_metrics = []

    for idx, url in enumerate(prom_urls):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{url}/metrics")
                text = resp.text
                node_metrics.append(
                    {
                        "nodeIndex": idx,
                        "nodeUrl": url,
                        "status": "available",
                        "metrics": {
                            "go_runtime": {
                                "gc_cycles": _extract_metric(
                                    text, "go_gc_cycles_total_gc_cycles_total"
                                ),
                                "heap_allocs": _extract_metric(
                                    text, "go_gc_heap_allocs_bytes_total"
                                ),
                                "goroutines": _extract_metric(text, "go_goroutines"),
                            },
                            "sync": {
                                "mutex_wait": _extract_metric(
                                    text, "go_sync_mutex_wait_total_seconds_total"
                                ),
                            },
                        },
                    }
                )
        except Exception as exc:
            node_metrics.append(
                {
                    "nodeIndex": idx,
                    "nodeUrl": url,
                    "status": "unavailable",
                    "error": str(exc),
                    "metrics": None,
                }
            )

    return {
        "totalNodes": len(prom_urls),
        "availableNodes": sum(1 for n in node_metrics if n["status"] == "available"),
        "nodes": node_metrics,
    }
