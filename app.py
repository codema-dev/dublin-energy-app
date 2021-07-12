from configparser import ConfigParser
from pathlib import Path

import geopandas as gpd
import pandas as pd
import streamlit as st

from dea import filter
from dea import io
from dea.mapselect import mapselect
from dea import CONFIG
from dea import _DATA_DIR


def main(data_dir: Path = _DATA_DIR, config: ConfigParser = CONFIG):
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
