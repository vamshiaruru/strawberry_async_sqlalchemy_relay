"""Settings module. The values can be loaded from env"""
import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseSettings

base_path = Path(__file__).parent


class Settings(BaseSettings):
    """Settings class"""

    # database
    database_dsn: str = ""

    # logging
    log_level: str = "info"

    # general
    static_dir: str = os.path.join(base_path, "static")

    # graphql
    max_query_depth: int = 100
    max_query_cost: int = 1000

    class Config:
        """pydantic's settings config"""

        env_file = os.getenv("SETTINGS_CONFIG") or base_path.joinpath("prod.env")


@lru_cache
def get_settings() -> Settings:
    return Settings()
