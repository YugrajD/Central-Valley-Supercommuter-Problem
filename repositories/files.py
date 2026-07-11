"""File-backed repository: Parquet for tables, GeoParquet for geographies.

Local default on machines without a Postgres server (no Docker here). Layout:
data/store/<name>.parquet — one file per table, geo tables carry their CRS in
the GeoParquet metadata.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd

from repositories.base import Repository

DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "data" / "store"


class FilesRepository(Repository):
    def __init__(self, root: Path | str = DEFAULT_ROOT):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        if not name.replace("_", "").isalnum():
            raise ValueError(f"table name must be alphanumeric/underscore: {name!r}")
        return self.root / f"{name}.parquet"

    def save_table(self, name: str, df: pd.DataFrame) -> None:
        df.to_parquet(self._path(name), index=False)

    def load_table(self, name: str) -> pd.DataFrame:
        return pd.read_parquet(self._path(name))

    def save_geo(self, name: str, gdf: gpd.GeoDataFrame) -> None:
        gdf.to_parquet(self._path(name), index=False)

    def load_geo(self, name: str) -> gpd.GeoDataFrame:
        return gpd.read_parquet(self._path(name))

    def exists(self, name: str) -> bool:
        return self._path(name).exists()

    def list_tables(self) -> list[str]:
        return sorted(p.stem for p in self.root.glob("*.parquet"))
