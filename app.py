from configparser import ConfigParser
from pathlib import Path

import geopandas as gpd
import streamlit as st

from dublin_energy_app import io
from dublin_energy_app.mapselect import mapselect
from dublin_energy_app import CONFIG
from dublin_energy_app import _DATA_DIR


def main(data_dir: Path = _DATA_DIR, config: ConfigParser = CONFIG):
    st.header("Welcome to the Dublin Retrofitting Tool")

    ## Load
    small_area_boundaries = _load_small_area_boundaries(
        url=config["urls"]["small_area_boundaries"], data_dir=data_dir
    )

    with st.form(key="Inputs"):
        st.markdown(" ℹ️ Click `Submit` once you've selected all parameters")
        selections = {}
        selections["ber_ratings"] = st.multiselect(
            "Select BER Ratings",
            options=["A", "B", "C", "D", "E", "F", "G"],
            default=["A", "B", "C", "D", "E", "F", "G"],
        )
        selections["small_areas"] = mapselect(
            column_name="small_area", boundaries=small_area_boundaries
        )
        inputs_are_submitted = st.form_submit_button(label="Submit")

    if inputs_are_submitted:
        ## Load ...
        pass


@st.cache
def _load_small_area_boundaries(url: str, data_dir: Path) -> gpd.GeoDataFrame:
    boundaries = io.load(
        read=gpd.read_parquet, url=url, data_dir=data_dir, filesystem_name="s3"
    )
    return boundaries


if __name__ == "__main__":
    main()
