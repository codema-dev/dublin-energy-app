from pathlib import Path
from typing import Callable
from typing import Any
from typing import Dict

import fsspec
import geopandas as gpd
import pandas as pd
import streamlit as st

from dea import filter


def _load(read: Callable, url: str, data_dir: Path, filesystem_name: str):
    filename = url.split("/")[-1]
    filepath = data_dir / filename
    if not filepath.exists():
        fs = fsspec.filesystem(filesystem_name)
        with fs.open(url, cache_storage=filepath) as f:
            df = read(f)
    else:
        df = read(filepath)
    return df


@st.cache
def load_small_area_boundaries(url: str, data_dir: Path) -> gpd.GeoDataFrame:
    return _load(
        read=gpd.read_parquet, url=url, data_dir=data_dir, filesystem_name="s3"
    )


def _load_buildings(url: str, data_dir: Path):
    return _load(read=pd.read_parquet, url=url, data_dir=data_dir, filesystem_name="s3")


@st.cache
def load_selected_buildings(
    url: str, data_dir: Path, selections: Dict[str, Any]
) -> pd.DataFrame:
    buildings = _load_buildings(url=url, data_dir=data_dir)
    return filter.get_selected_buildings(buildings=buildings, selections=selections)
