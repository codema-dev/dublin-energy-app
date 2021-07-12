from configparser import ConfigParser
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Union

import geopandas as gpd
import pandas as pd
import streamlit as st

from dea import filter
from dea import io
from dea.mapselect import mapselect
from dea import CONFIG
from dea import DEFAULTS
from dea import _DATA_DIR

DeaSelection = Dict[str, Dict[str, Union[int, Dict[str, int]]]]


def main(
    defaults: DeaSelection = DEFAULTS,
    data_dir: Path = _DATA_DIR,
    config: ConfigParser = CONFIG,
):
    st.header("Welcome to the Dublin Retrofitting Tool")

    ## Load
    small_area_boundaries = _load_small_area_boundaries(
        url=config["urls"]["small_area_boundaries"], data_dir=data_dir
    )

    with st.form(key="Inputs"):
        st.markdown("ℹ️ Click `Submit` once you've selected all parameters")
        selections = {}
        selections["energy_rating"] = st.multiselect(
            "Select BER Ratings",
            options=["A", "B", "C", "D", "E", "F", "G"],
            default=["A", "B", "C", "D", "E", "F", "G"],
        )
        selections["small_area"] = mapselect(
            column_name="small_area", boundaries=small_area_boundaries
        )
        selections["retrofit"] = _retrofitselect(defaults)
        inputs_are_submitted = st.form_submit_button(label="Submit")

    if inputs_are_submitted:
        ## Load ...
        buildings = _load_buildings(config["urls"]["bers"], data_dir=data_dir)

        filtered_buildings = buildings.pipe(
            filter.filter_by_substrings,
            column_name="energy_rating",
            selected_substrings=selections["energy_rating"],
            all_substrings=["A", "B", "C", "D", "E", "F", "G"],
        ).pipe(
            filter.filter_by_substrings,
            column_name="small_area",
            selected_substrings=selections["small_area"],
            all_substrings=small_area_boundaries["small_area"],
        )


def _retrofitselect(defaults: DeaSelection) -> DeaSelection:
    selections = defaults.copy()
    with st.beta_expander(label="Change Default Costs & Threshold Values"):
        for component, properties in defaults.items():
            selections[component]["uvalue"]["target"] = st.number_input(
                label="Threshold U-Value [W/m²K] - assume no retrofits below this value",
                min_value=float(0),
                value=properties["uvalue"]["target"],
                key=component,
                step=0.05,
            )
            c1, c2 = st.beta_columns(2)
            selections[component]["cost"]["lower"] = c1.number_input(
                label="Lowest* Likely Cost [€/m²]",
                min_value=0,
                value=properties["cost"]["lower"],
                key=component,
                step=5,
            )
            selections[component]["cost"]["upper"] = c2.number_input(
                label="Highest** Likely Cost [€/m²]",
                min_value=0,
                value=properties["cost"]["upper"],
                key=component,
                step=5,
            )
            footnote = f"""
                <small> * {properties["typical_area"] * properties["cost"]["lower"]}€
                for a typical {component} area of {properties["typical_area"]}m²<br>
                ** {properties["typical_area"]  * properties["cost"]["upper"]}€
                for a typical {component} area of {properties["typical_area"]}m²</small>
                """
            st.markdown(footnote, unsafe_allow_html=True)

    return selections


@st.cache
def _load_small_area_boundaries(url: str, data_dir: Path) -> gpd.GeoDataFrame:
    return io.load(
        read=gpd.read_parquet, url=url, data_dir=data_dir, filesystem_name="s3"
    )


@st.cache
def _load_buildings(url: str, data_dir: Path):
    # Remove NS or Not stated buildings until ibsg can replace them with SA modes
    return io.load(
        read=pd.read_parquet, url=url, data_dir=data_dir, filesystem_name="s3"
    ).query("period_built != 'NS'")


if __name__ == "__main__":
    main()
