from __future__ import annotations

import os
from typing import Optional

from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ChainConfig(BaseModel):
    execution_rpc_url: Optional[list[str]] = None
    consensus_api_url: Optional[list[str]] = None
    prometheus_url: Optional[list[str]] = None


def _parse_url_list(value: Optional[str]) -> Optional[list[str]]:
    if not value:
        return None
    return [u.strip() for u in value.split(",") if u.strip()]


def _discover_chains() -> dict[str, ChainConfig]:
    suffixes = ("_EXECUTION_RPC_URL", "_CONSENSUS_API_URL", "_PROMETHEUS_URL")
    chain_names: dict[str, str] = {}

    for key in os.environ:
        for suffix in suffixes:
            if key.endswith(suffix):
                chain = key.removesuffix(suffix)
                if chain and chain != "DEFAULT":
                    chain_names[chain.lower()] = chain
                break

    configs: dict[str, ChainConfig] = {}
    for lower_name, original_name in chain_names.items():
        configs[lower_name] = ChainConfig(
            execution_rpc_url=_parse_url_list(
                os.environ.get(f"{original_name}_EXECUTION_RPC_URL")
            ),
            consensus_api_url=_parse_url_list(
                os.environ.get(f"{original_name}_CONSENSUS_API_URL")
            ),
            prometheus_url=_parse_url_list(
                os.environ.get(f"{original_name}_PROMETHEUS_URL")
            ),
        )

    return configs


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    port: int = 8881
    host: str = "0.0.0.0"
    jwt_secret: str
    mongo_uri: str
    default_max_rps: int = 10
    default_daily_requests: int = 10000

    # Cached once at startup — env vars don't change at runtime.
    _chains: dict[str, ChainConfig] = {}

    @property
    def chains(self) -> dict[str, ChainConfig]:
        if not self._chains:
            object.__setattr__(self, "_chains", _discover_chains())
        return self._chains

    def get_chain_config(self, chain_name: str) -> Optional[ChainConfig]:
        return self.chains.get(chain_name.lower())

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("JWT_SECRET must not be empty")
        return v

    @field_validator("mongo_uri")
    @classmethod
    def mongo_uri_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("MONGO_URI must not be empty")
        return v


settings = Settings()
