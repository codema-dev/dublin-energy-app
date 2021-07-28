from pathlib import Path
from typing import Callable
from typing import List

import fsspec
import geopandas as gpd
import pandas as pd
import streamlit as st

from dea import filter
from dea import retrofit


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


def _add_retrofit_columns(buildings: pd.DataFrame) -> pd.DataFrame:
    buildings["total_floor_area"] = (
        buildings["ground_floor_area"]
        + buildings["first_floor_area"]
        + buildings["second_floor_area"]
        + buildings["third_floor_area"]
    )
    return retrofit.calculate_fabric_heat_loss(buildings)


@st.cache
def load_selected_buildings(
    url: str,
    data_dir: Path,
    selected_energy_ratings: List[str],
    selected_small_areas: List[str],
) -> pd.DataFrame:
    buildings = _load_buildings(url=url, data_dir=data_dir)
    buildings_with_retrofit_columns = _add_retrofit_columns(buildings)
    return filter.get_selected_buildings(
        buildings=buildings_with_retrofit_columns,
        selected_energy_ratings=selected_energy_ratings,
        selected_small_areas=selected_small_areas,
    )
