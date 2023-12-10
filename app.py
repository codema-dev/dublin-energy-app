from configparser import ConfigParser
from pathlib import Path
from typing import Any
from typing import Dict

import streamlit as st

from dea import CONFIG
from dea import DEFAULTS
from dea import _DATA_DIR
from dea import filter
from dea import io
from dea import plot
from dea.mapselect import mapselect 
from dea import retrofit
import os


import toml

# Read values from the TOML file
config = toml.load("config.toml")

# Access AWS credentials
aws_access_key_id = config["aws"]["access_key_id"]
aws_secret_access_key = config["aws"]["secret_access_key"]


# Debugging print statements
print(f"AWS Access Key ID: {aws_access_key_id}")
print(f"AWS Secret Access Key: {aws_secret_access_key}")



DeaSelection = Dict[str, Any]

@st.cache_data
def load_small_area_boundaries(small_area_boundaries_url, data_dir):
    return io.load_small_area_boundaries(
        url=small_area_boundaries_url, data_dir=data_dir
    )

def main(
    defaults: DeaSelection = DEFAULTS,
    data_dir: Path = _DATA_DIR,
    config: ConfigParser = CONFIG,
):
    st.header("Welcome to the Dublin Retrofitting Tool")

    small_area_boundaries_url = config["urls"]["small_area_boundaries"]
    small_area_boundaries = load_small_area_boundaries(small_area_boundaries_url, data_dir)


    with st.form(key="Inputs"):
        st.markdown("ℹ️ Click `Submit` once you've selected all parameters")
        selected_energy_ratings = st.multiselect(
            "Select BER Ratings",
            options=["A", "B", "C", "D", "E", "F", "G"],
            default=["A", "B", "C", "D", "E", "F", "G"],
        )
        selected_small_areas = mapselect(
            column_name="small_area", boundaries=small_area_boundaries
        )
        retrofit_selections = _retrofitselect(defaults)
        inputs_are_submitted = st.form_submit_button(label="Submit")

    if inputs_are_submitted:
        pre_retrofit = io.load_selected_buildings(
            url=config["urls"]["bers"],
            data_dir=data_dir,
            selected_energy_ratings=selected_energy_ratings,
            selected_small_areas=selected_small_areas,
        )

        with st.spinner("Retrofitting buildings..."):
            post_retrofit = retrofit.retrofit_buildings(
                buildings=pre_retrofit, selections=retrofit_selections
            )

        pre_vs_post_bers = retrofit.calculate_ber_improvement(
            pre_retrofit=pre_retrofit, post_retrofit=post_retrofit
        )
        pre_vs_post_hps = retrofit.calculate_heat_pump_viability_improvement(
            pre_retrofit=pre_retrofit, post_retrofit=post_retrofit
        )

        plot.plot_ber_rating_comparison(pre_vs_post_bers)
        plot.plot_heat_pump_viability_comparison(pre_vs_post_hps)
        plot.plot_retrofit_costs(post_retrofit=post_retrofit)


def _retrofitselect(defaults: DeaSelection) -> DeaSelection:
    selections = defaults.copy()
    for component, properties in defaults.items():
        with st.expander(label=f"Change {component} defaults"):
            selections[component]["uvalue"]["target"] = st.number_input(
                label="Threshold U-Value [W/m²K] - assume no retrofits below this value",
                min_value=float(0),
                value=properties["uvalue"]["target"],
                key=component + "_threshold",
                step=0.05,
            )
            c1, c2 = st.columns(2)
            selections[component]["cost"]["lower"] = c1.number_input(
                label="Lowest* Likely Cost [€/m²]",
                min_value=0,
                value=properties["cost"]["lower"],
                key=component + "_cost_lower",
                step=5,
            )
            selections[component]["cost"]["upper"] = c2.number_input(
                label="Highest** Likely Cost [€/m²]",
                min_value=0,
                value=properties["cost"]["upper"],
                key=component + "_cost_upper",
                step=5,
            )
            footnote = f"""
                <small> * {properties["typical_area"] * properties["cost"]["lower"]}€
                for a typical {component} area of {properties["typical_area"]}m²<br>
                ** {properties["typical_area"]  * properties["cost"]["upper"]}€
                for a typical {component} area of {properties["typical_area"]}m²</small>
                """
            st.markdown(footnote, unsafe_allow_html=True)

        selections[component]["percentage_selected"] = st.slider(
            f"""% of viable {component}s retrofitted to U-Value =
            {selections[component]['uvalue']['target']} [W/m²K]""",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            key=component + "_percentage",
        )

    return selections


if __name__ == "__main__":
    main()
