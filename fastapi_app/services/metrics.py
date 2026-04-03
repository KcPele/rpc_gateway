from __future__ import annotations

import httpx
from prometheus_client import Counter, Gauge, Histogram, generate_latest

# Shared client for health checks — avoids creating a new connection pool each call.
_health_client = httpx.AsyncClient(timeout=10.0)

from fastapi_app.config.settings import settings

http_requests_total = Counter(
    "rpc_gateway_requests_total",
    "Total number of HTTP requests",
    ["user_id", "api_key", "path", "method", "status_code"],
)

http_request_duration = Histogram(
    "rpc_gateway_request_duration_seconds",
    "HTTP request latency in seconds",
    ["user_id", "api_key", "path", "method"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10],
)

active_connections = Gauge(
    "rpc_gateway_active_connections",
    "Number of active connections",
)

rpc_requests_total = Counter(
    "rpc_requests_total",
    "Total number of RPC requests",
    ["user_id", "api_key", "rpc_method", "endpoint_type"],
)

rpc_request_duration = Histogram(
    "rpc_request_duration_seconds",
    "RPC request latency in seconds",
    ["user_id", "api_key", "rpc_method", "endpoint_type"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10, 30],
)

rate_limit_hits = Counter(
    "rpc_gateway_rate_limit_hits_total",
    "Total number of rate limit hits",
    ["user_id", "api_key"],
)

user_daily_requests = Gauge(
    "rpc_gateway_user_daily_requests",
    "Number of requests made by user today",
    ["user_id", "api_key"],
)

node_execution_syncing = Gauge(
    "ethereum_execution_syncing",
    "Whether the execution layer is syncing (1) or not (0)",
)

node_consensus_syncing = Gauge(
    "ethereum_consensus_syncing",
    "Whether the consensus layer is syncing (1) or not (0)",
)

node_consensus_head_slot = Gauge(
    "ethereum_consensus_head_slot",
    "Current head slot of the consensus layer",
)

node_health_status = Gauge(
    "ethereum_node_health_status",
    "Overall node health status (1=healthy, 0.5=degraded, 0=unhealthy)",
)

node_prometheus_metrics_available = Gauge(
    "ethereum_prometheus_metrics_available",
    "Whether Prometheus metrics are available (1) or not (0)",
)

node_runtime_gc_cycles = Gauge(
    "ethereum_node_gc_cycles_total",
    "Total GC cycles from the Ethereum node",
)

node_runtime_heap_allocs = Gauge(
    "ethereum_node_heap_allocs_bytes",
    "Total heap allocations from the Ethereum node",
)


def record_rpc_metrics(
    user_id: str,
    api_key: str,
    rpc_method: str,
    endpoint_type: str,
    duration: float,
) -> None:
    rpc_requests_total.labels(
        user_id=user_id,
        api_key=api_key,
        rpc_method=rpc_method,
        endpoint_type=endpoint_type,
    ).inc()

    rpc_request_duration.labels(
        user_id=user_id,
        api_key=api_key,
        rpc_method=rpc_method,
        endpoint_type=endpoint_type,
    ).observe(duration)


def record_rate_limit_hit(user_id: str, api_key: str) -> None:
    rate_limit_hits.labels(user_id=user_id, api_key=api_key).inc()


def _extract_metric_value(metrics_text: str, metric_name: str) -> float | None:
    for line in metrics_text.split("\n"):
        if not line.startswith("#") and metric_name in line:
            parts = line.split()
            if len(parts) >= 2 and parts[0] == metric_name:
                try:
                    return float(parts[1])
                except ValueError:
                    return None
    return None


async def update_ethereum_node_metrics(chain_name: str) -> None:
    chain_config = settings.get_chain_config(chain_name)
    if not chain_config:
        node_health_status.set(0)
        node_prometheus_metrics_available.set(0)
        return

    exec_urls = chain_config.execution_rpc_url or []
    cons_urls = chain_config.consensus_api_url or []
    prom_urls = chain_config.prometheus_url or []

    exec_ok = False
    cons_ok = False
    prom_ok = False

    if exec_urls:
        try:
            resp = await _health_client.post(
                exec_urls[0],
                json={"jsonrpc": "2.0", "method": "eth_syncing", "params": [], "id": 1},
            )
            result = resp.json().get("result")
            node_execution_syncing.set(0 if result is False else 1)
            exec_ok = True
        except Exception:
            node_execution_syncing.set(1)

    if cons_urls:
        try:
            resp = await _health_client.get(f"{cons_urls[0]}/eth/v1/node/syncing")
            sync_data = resp.json().get("data", {})
            node_consensus_syncing.set(1 if sync_data.get("is_syncing") else 0)
            try:
                node_consensus_head_slot.set(int(sync_data.get("head_slot", 0)))
            except (ValueError, TypeError):
                pass
            cons_ok = True
        except Exception:
            pass

    if prom_urls:
        try:
            resp = await _health_client.get(f"{prom_urls[0]}/metrics")
            text = resp.text
            node_prometheus_metrics_available.set(1)
            prom_ok = True
            gc = _extract_metric_value(text, "go_gc_cycles_total_gc_cycles_total")
            if gc is not None:
                node_runtime_gc_cycles.set(gc)
            heap = _extract_metric_value(text, "go_gc_heap_allocs_bytes_total")
            if heap is not None:
                node_runtime_heap_allocs.set(heap)
        except Exception:
            node_prometheus_metrics_available.set(0)

    healthy_count = sum([exec_ok, cons_ok])
    total_checked = 2
    ratio = healthy_count / total_checked if total_checked > 0 else 0

    if ratio == 1:
        node_health_status.set(1)
    elif ratio >= 0.5:
        node_health_status.set(0.5)
    else:
        node_health_status.set(0)


def _init_custom_metrics() -> None:
    http_requests_total.labels(
        user_id="init",
        api_key="init",
        path="/init",
        method="GET",
        status_code="200",
    ).inc(0)

    http_request_duration.labels(
        user_id="init",
        api_key="init",
        path="/init",
        method="GET",
    ).observe(0)

    active_connections.set(0)

    rpc_requests_total.labels(
        user_id="init",
        api_key="init",
        rpc_method="init",
        endpoint_type="execution",
    ).inc(0)

    rpc_request_duration.labels(
        user_id="init",
        api_key="init",
        rpc_method="init",
        endpoint_type="execution",
    ).observe(0)

    rate_limit_hits.labels(user_id="init", api_key="init").inc(0)
    user_daily_requests.labels(user_id="init", api_key="init").set(0)


def get_metrics() -> bytes:
    return generate_latest()


_init_custom_metrics()
