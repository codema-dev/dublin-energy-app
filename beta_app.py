import json
from pathlib import Path
from typing import Any, Dict
from typing import List
from typing import Tuple
from altair.vegalite.v4.schema.core import Data

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


@st.cache
def load_building_stock(data_dir: Path) -> Tuple[DataFrame]:
    index_columns = ["SMALL_AREA", "dwelling_type", "period_built", "category_id"]
    known_indiv_hh = (
        pd.read_parquet(data_dir / "dublin_indiv_hhs_known.parquet")
        .rename(columns={"Wall weighted Uvalue": "wall_uvalue"})
        .set_index(index_columns)
    )
    unknown_indiv_hh = (
        pd.read_parquet(data_dir / "dublin_indiv_hhs_unknown.parquet")
        .rename(columns={"Wall weighted Uvalue": "wall_uvalue"})
        .set_index(index_columns)
    )
    return known_indiv_hh, unknown_indiv_hh


@st.cache
def load_geodata(data_dir: Path) -> Tuple[GeoDataFrame]:
    return gpd.read_file(
        data_dir / "dublin_small_area_boundaries_2011.geojson", driver="GeoJSON"
    ).to_crs(epsg=4326)


@st.cache
def load_archetypes(data_dir: Path) -> Tuple[DataFrame]:

    wall_type_archetypes = pd.read_csv(
        data_dir / "most_common_wall_types_by_archetype.csv",
    ).set_index(["dwelling_type", "period_built"])

    wall_uvalue_defaults = pd.read_csv(
        data_dir / "deap-default-wall-uvalues-by-period-built.csv"
    ).set_index(["most_significant_wall_type", "period_built"])

    with open(data_dir / "archetype_new_build.json", "r") as file:
        new_build_archetype = pd.Series(json.load(file))

    return (
        wall_type_archetypes,
        wall_uvalue_defaults,
        new_build_archetype,
    )


@st.cache
def load_misc_data(data_dir: Path) -> Tuple[Any]:
    with open(DATA_DIR / "electoral_districts.json", "r") as file:
        electoral_districts = [None] + json.load(file)

    esri_forecast = pd.read_csv(data_dir / "esri_housing_forecast_12_2020.csv")

    return (
        electoral_districts,
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

## Load data.
(
    known_indiv_hh,
    unknown_indiv_hh,
) = load_building_stock(data_dir)
small_area_boundaries = load_geodata(data_dir)
(
    wall_type_archetypes,
    wall_uvalue_defaults,
    new_build_archetype,
) = load_archetypes(data_dir)
(
    electoral_districts,
    esri_forecast,
) = load_misc_data(data_dir)

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
    st.write(
        wall_type_archetypes.reset_index().pipe(_convert_categorical_columns_to_str)
    )

wall_types = archetypes.estimate_type_of_wall(
    known_indiv_hh,
    unknown_indiv_hh,
    wall_type_archetypes,
    on=wall_type_archetypes.index.names,
)
wall_uvalue_defaults = archetypes.estimate_uvalue_of_wall(
    known_indiv_hh,
    unknown_indiv_hh,
    wall_type_archetypes,
)