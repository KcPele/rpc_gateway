from __future__ import annotations

from datetime import datetime, timezone

from beanie import PydanticObjectId
from fastapi import HTTPException, Query, status

from fastapi_app.database import App, Chain, DefaultAppSettings, User
from fastapi_app.middleware.admin import require_admin
from fastapi_app.middleware.auth import get_current_user
from fastapi_app.services.node_health import (
    check_consensus_nodes,
    check_execution_nodes,
    check_prometheus_nodes,
    collect_node_metrics,
    compute_overall_health,
)
from fastapi_app.config.settings import settings


def router_dependencies():
    """Return shared dependencies for admin routes."""
    return {
        "require_admin": require_admin,
        "get_current_user": get_current_user,
    }


async def get_node_health(chain: str) -> dict:
    """Get node health for a chain."""
    chain_name = chain.lower()
    chain_config = settings.get_chain_config(chain_name)

    if not chain_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration not found or incomplete for chain: {chain_name}.",
        )

    exec_urls = chain_config.execution_rpc_url or []
    cons_urls = chain_config.consensus_api_url or []
    prom_urls = chain_config.prometheus_url or []

    exec_results = await check_execution_nodes(exec_urls)
    cons_results = await check_consensus_nodes(cons_urls)
    prom_results = await check_prometheus_nodes(prom_urls)

    overall = compute_overall_health(
        exec_urls, cons_urls, prom_urls, exec_results, cons_results, prom_results
    )

    return {
        "success": True,
        "data": {
            "chain": chain_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "execution": {
                "status": "healthy"
                if any(n["status"] == "available" for n in exec_results)
                else "unhealthy"
                if exec_urls
                else "not_configured",
                "totalNodes": len(exec_urls),
                "availableNodes": sum(
                    1 for n in exec_results if n["status"] == "available"
                ),
                "nodes": exec_results,
            },
            "consensus": {
                "status": "healthy"
                if any(n["status"] == "available" for n in cons_results)
                else "unhealthy"
                if cons_urls
                else "not_configured",
                "totalNodes": len(cons_urls),
                "availableNodes": sum(
                    1 for n in cons_results if n["status"] == "available"
                ),
                "nodes": cons_results,
            },
            "metrics": {
                "status": "available"
                if any(n["status"] == "available" for n in prom_results)
                else "unavailable"
                if prom_urls
                else "not_configured",
                "totalNodes": len(prom_urls),
                "availableNodes": sum(
                    1 for n in prom_results if n["status"] == "available"
                ),
                "nodes": prom_results,
            },
            "overall": overall,
        },
    }


async def get_node_metrics(chain: str) -> dict:
    """Get node metrics for a chain."""
    chain_name = chain.lower()
    metrics_data = await collect_node_metrics(chain_name)

    return {
        "success": True,
        "data": {
            "chain": chain_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **metrics_data,
        },
    }


async def list_chains() -> dict:
    """List all chains."""
    chains = await Chain.find().sort("-created_at").to_list()
    return {
        "success": True,
        "data": [
            {
                "_id": str(c.id),
                "name": c.name,
                "chainId": int(c.chain_id) if c.chain_id.isdigit() else c.chain_id,
                "isEnabled": c.is_enabled,
                "adminNotes": c.admin_notes,
                "createdAt": c.created_at,
                "updatedAt": c.updated_at,
            }
            for c in chains
        ],
    }


async def add_chain(payload: dict) -> dict:
    """Add a new chain."""
    name = payload.get("name")
    chain_id = payload.get("chainId") or payload.get("chain_id")
    is_enabled = payload.get("isEnabled", payload.get("is_enabled", True))
    admin_notes = payload.get("adminNotes", payload.get("admin_notes"))

    if not name or not chain_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields: name, chainId.",
        )

    existing = await Chain.find_one({"$or": [{"name": name}, {"chain_id": chain_id}]})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Chain with name '{name}' or chainId '{chain_id}' already exists.",
        )

    now = datetime.now(timezone.utc)
    new_chain = Chain(
        name=name,
        chain_id=str(chain_id),
        is_enabled=is_enabled,
        admin_notes=admin_notes,
        created_at=now,
        updated_at=now,
    )
    await new_chain.insert()

    return {
        "success": True,
        "message": "Chain added successfully.",
        "data": {
            "_id": str(new_chain.id),
            "name": new_chain.name,
            "chainId": int(new_chain.chain_id)
            if new_chain.chain_id.isdigit()
            else new_chain.chain_id,
            "isEnabled": new_chain.is_enabled,
            "adminNotes": new_chain.admin_notes,
            "createdAt": new_chain.created_at,
            "updatedAt": new_chain.updated_at,
        },
    }


async def update_chain(chain_id: str, payload: dict) -> dict:
    """Update an existing chain."""
    name = payload.get("name")
    new_chain_id = payload.get("newChainId", payload.get("new_chain_id"))
    is_enabled = payload.get("isEnabled", payload.get("is_enabled"))
    admin_notes = payload.get("adminNotes", payload.get("admin_notes"))

    if (
        name is None
        and new_chain_id is None
        and is_enabled is None
        and admin_notes is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update fields provided.",
        )

    chain = await Chain.find_one(Chain.chain_id == chain_id)
    if not chain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chain with chainId '{chain_id}' not found.",
        )

    if name and name != chain.name:
        conflict = await Chain.find_one(Chain.name == name)
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Another chain with name '{name}' already exists.",
            )
        chain.name = name

    if new_chain_id and new_chain_id != chain.chain_id:
        conflict = await Chain.find_one(Chain.chain_id == new_chain_id)
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Another chain with chainId '{new_chain_id}' already exists.",
            )
        chain.chain_id = new_chain_id

    if is_enabled is not None:
        chain.is_enabled = is_enabled
    if admin_notes is not None:
        chain.admin_notes = admin_notes

    chain.updated_at = datetime.now(timezone.utc)
    await chain.save()

    return {
        "success": True,
        "message": "Chain updated successfully.",
        "data": {
            "_id": str(chain.id),
            "name": chain.name,
            "chainId": int(chain.chain_id)
            if chain.chain_id.isdigit()
            else chain.chain_id,
            "isEnabled": chain.is_enabled,
            "adminNotes": chain.admin_notes,
            "createdAt": chain.created_at,
            "updatedAt": chain.updated_at,
        },
    }


async def delete_chain(chain_id: str) -> dict:
    """Delete a chain."""
    chain = await Chain.find_one(Chain.chain_id == chain_id)
    if not chain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chain with chainId '{chain_id}' not found.",
        )

    await chain.delete()

    return {
        "success": True,
        "message": "Chain deleted successfully.",
    }
