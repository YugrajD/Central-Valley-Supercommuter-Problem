"""Storage interface. Business logic and pipeline code depend on this, never on a backend.

Backends: FilesRepository (GeoParquet, local default), PostgresRepository (PostGIS).
A future Snowflake implementation slots in here without touching callers (CLAUDE.md §8).
"""

from abc import ABC, abstractmethod

import geopandas as gpd
import pandas as pd


class Repository(ABC):
    """Named-table storage for plain and geo dataframes."""

    @abstractmethod
    def save_table(self, name: str, df: pd.DataFrame) -> None: ...

    @abstractmethod
    def load_table(self, name: str) -> pd.DataFrame: ...

    @abstractmethod
    def save_geo(self, name: str, gdf: gpd.GeoDataFrame) -> None: ...

    @abstractmethod
    def load_geo(self, name: str) -> gpd.GeoDataFrame: ...

    @abstractmethod
    def exists(self, name: str) -> bool: ...

    @abstractmethod
    def list_tables(self) -> list[str]: ...


def get_repository() -> Repository:
    """Local default. Swap by setting ALTAMONT_STORAGE=postgres (with ALTAMONT_PG_DSN)."""
    import os

    if os.environ.get("ALTAMONT_STORAGE") == "postgres":
        from repositories.postgres import PostgresRepository

        return PostgresRepository(os.environ["ALTAMONT_PG_DSN"])

    from repositories.files import FilesRepository

    return FilesRepository()
