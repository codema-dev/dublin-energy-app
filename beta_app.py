import json
from pathlib import Path
from typing import Any, Dict
from typing import List
from typing import Tuple

import geopandas as gpd
from geopandas import GeoDataFrame
import numpy as np
import pandas as pd
from pandas import DataFrame
from pandas.core.series import Series
import plotly.express as px
import streamlit as st

from dublin_energy_app import archetypes

KWH_TO_MWH = 10 ** -3
DATA_DIR = Path("./data")
LOCAL_AUTHORITIES = [
    None,
    "Dublin City",
    "South Dublin",
    "Fingal",
    "Dún Laoghaire-Rathdown",
]
INDEX_COLUMNS = ["SMALL_AREA", "dwelling_type", "period_built", "category_id"]


@st.cache
def load_data(
    data_dir: Path,
    index_columns: List[str],
) -> Tuple[Any]:

    known_indiv_hh = pd.read_parquet(
        data_dir / "dublin_indiv_hhs_known.parquet"
    ).set_index(INDEX_COLUMNS)

    unknown_indiv_hh = pd.read_parquet(
        data_dir / "dublin_indiv_hhs_unknown.parquet"
    ).set_index(INDEX_COLUMNS)

    small_area_boundaries = gpd.read_file(
        data_dir / "dublin_small_area_boundaries_2011.geojson", driver="GeoJSON"
    ).to_crs(epsg=4326)

    with open(DATA_DIR / "electoral_districts.json", "r") as file:
        electoral_districts = [None] + json.load(file)

    wall_archetypes = pd.read_csv(
        data_dir / "most_common_wall_types_by_archetype.csv",
    ).set_index(["dwelling_type", "period_built"])

    with open(data_dir / "archetype_new_build.json", "r") as file:
        new_build_archetype = pd.Series(json.load(file))

    esri_forecast = pd.read_csv(data_dir / "esri_housing_forecast_12_2020.csv")

    return (
        known_indiv_hh,
        unknown_indiv_hh,
        small_area_boundaries,
        electoral_districts,
        wall_archetypes,
        new_build_archetype,
        esri_forecast,
    )


def _convert_categorical_columns_to_str(df: DataFrame) -> DataFrame:
    # NOTE: streamlit doesn't yet support st.write for categorical dtypes
    column_dtypes = df.dtypes.to_dict()
    categorical_column_dtypes = {
        k: str for k, v in column_dtypes.items() if isinstance(v, pd.CategoricalDtype)
    }
    return df.astype(categorical_column_dtypes)


data_dir = Path("./data")

st.title("Dublin Housing Energy Demand App")
(
    known_indiv_hh,
    unknown_indiv_hh,
    small_area_boundaries,
    electoral_districts,
    wall_archetypes,
    new_build_archetype,
    esri_forecast,
) = load_data(data_dir, INDEX_COLUMNS)

if st.checkbox("Show sample of known building stock?"):
    text = (
        "<strong>Source:</strong> BER public geocoded to Small Area level by SEAI"
        " (July, 2020)"
    )
    st.markdown(text, unsafe_allow_html=True)
    st.write(
        known_indiv_hh.sample(50)
        .reset_index()
        .pipe(_convert_categorical_columns_to_str)
    )

if st.checkbox("Show wall archetypes?"):
    text = (
        "<strong>Source:</strong> Derived from SEAI's BER public dataset (June, 2021)"
    )
    st.markdown(text, unsafe_allow_html=True)
    st.write(wall_archetypes.reset_index().pipe(_convert_categorical_columns_to_str))

wall_types = archetypes.estimate_type_of_wall(
    known_indiv_hh,
    unknown_indiv_hh,
    wall_archetypes,
    on=wall_archetypes.index.names,
)