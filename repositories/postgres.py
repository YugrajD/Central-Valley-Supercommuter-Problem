"""PostGIS repository — the deploy-target backend (Supabase/Cloud SQL).

Requires: pip install sqlalchemy psycopg2-binary geoalchemy2
Same interface as FilesRepository; callers never see the difference.
"""

import geopandas as gpd
import pandas as pd

from repositories.base import Repository


class PostgresRepository(Repository):
    def __init__(self, dsn: str):
        try:
            from sqlalchemy import create_engine
        except ImportError as e:
            raise ImportError(
                "Postgres backend needs: pip install sqlalchemy psycopg2-binary geoalchemy2"
            ) from e
        self.engine = create_engine(dsn)

    def save_table(self, name: str, df: pd.DataFrame) -> None:
        df.to_sql(name, self.engine, if_exists="replace", index=False)

    def load_table(self, name: str) -> pd.DataFrame:
        return pd.read_sql_table(name, self.engine)

    def save_geo(self, name: str, gdf: gpd.GeoDataFrame) -> None:
        gdf.to_postgis(name, self.engine, if_exists="replace", index=False)

    def load_geo(self, name: str) -> gpd.GeoDataFrame:
        return gpd.read_postgis(f'SELECT * FROM "{name}"', self.engine, geom_col="geometry")

    def exists(self, name: str) -> bool:
        from sqlalchemy import inspect

        return name in inspect(self.engine).get_table_names()

    def list_tables(self) -> list[str]:
        from sqlalchemy import inspect

        return sorted(inspect(self.engine).get_table_names())
