from pathlib import Path
from typing import Callable

import fsspec
import geopandas as gpd
import pandas as pd
import streamlit as st


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


@st.cache
def load_buildings(url: str, data_dir: Path):
    return _load(read=pd.read_parquet, url=url, data_dir=data_dir, filesystem_name="s3")
