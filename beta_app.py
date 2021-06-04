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

from dublin_energy_app.deap import calculate_heat_loss_parameter
from dublin_energy_app import dashboard

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


def estimate_wall_types(
    known_indiv_hh: DataFrame,
    unknown_indiv_hh: DataFrame,
    wall_archetypes: DataFrame,
    index_columns: List[str],
) -> DataFrame:
    wall_type_is_known = known_indiv_hh["most_significant_wall_type"].notnull()
    unknown_wall_types = pd.concat(
        [
            known_indiv_hh[~wall_type_is_known]["most_significant_wall_type"],
            unknown_indiv_hh["most_significant_wall_type"],
        ]
    )
    estimated_wall_types = (
        unknown_wall_types.reset_index()
        .set_index(["dwelling_type", "period_built"])
        .combine_first(
            wall_archetypes.rename(columns={"WallType": "most_significant_wall_type"})
        )
        .reset_index()
        .set_index(INDEX_COLUMNS)
    )
    return pd.concat(
        [
            known_indiv_hh[wall_type_is_known][["most_significant_wall_type"]],
            estimated_wall_types,
        ]
    )


def show_housing_projections(esri_forecast):
    if st.checkbox("Show Housing Demand Projections"):
        st.subheader(
            "Structural Housing Demand Projections By Local Authority 2017-2014"
        )
        st.markdown(
            "These housing demand projections are used to estimate the housing demand in"
            " Dublin at any given year."
        )
        st.markdown(
            "*__Source__: Bergin, A. and García-Rodríguez, A., 2020."
            " Regional demographics and structural housing demand at a county Level."
            " ESRI, Economic & Social Research Institute.*"
        )
        st.write(esri_forecast)


def show_housing_sample(stock):
    if st.checkbox("Show Individual Housing Sample"):
        st.markdown(
            "This is a sample of the individual households used in the demand calculation"
        )
        sample = stock.sample(50).reset_index()

        # NOTE: streamlit doesn't yet support st.write for categorical dtypes
        column_dtypes = sample.dtypes.to_dict()
        categorical_columns = {
            k: str
            for k, v in column_dtypes.items()
            if isinstance(v, pd.CategoricalDtype)
        }
        st.write(sample.astype(categorical_columns))


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

show_housing_sample(known_indiv_hh)

wall_types = estimate_wall_types(
    known_indiv_hh, unknown_indiv_hh, wall_archetypes, INDEX_COLUMNS
)
