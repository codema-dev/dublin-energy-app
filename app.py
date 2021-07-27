cfrom configparser import ConfigParser
from pathlib import Path
from typing import Any
from typing import Dict

import altair as alt
import geopandas as gpd
import icontract
import numpy as np
import pandas as pd
import streamlit as st

from dea import CONFIG
from dea import DEFAULTS
from dea import _DATA_DIR
from dea import filter
from dea import io
from dea.mapselect import mapselect
from dea import retrofit

DeaSelection = Dict[str, Any]


def main(
    defaults: DeaSelection = DEFAULTS,
    data_dir: Path = _DATA_DIR,
    config: ConfigParser = CONFIG,
):
    st.header("Welcome to the Dublin Retrofitting Tool")

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
        buildings = _load_buildings(config["urls"]["bers"], data_dir=data_dir)

        with st.spinner("Getting selected buildings..."):
            filtered_buildings = _filter_buildings(
                buildings=buildings, selections=selections
            )

        with st.spinner("Retrofitting buildings..."):
            retrofitted_buildings = retrofit.retrofit_buildings(
                buildings=filtered_buildings, selections=selections
            )

        with st.spinner("Calculating BER improvement..."):
            pre_vs_post_retrofit_bers = retrofit.calculate_ber_improvement(
                pre_retrofit=filtered_buildings, post_retrofit=retrofitted_buildings
            )

        _plot_ber_rating_comparison(pre_vs_post_retrofit_bers)
        _plot_retrofit_costs(post_retrofit=retrofitted_buildings)


def _retrofitselect(defaults: DeaSelection) -> DeaSelection:
    selections = defaults.copy()
    for component, properties in defaults.items():
        with st.beta_expander(label=f"Change {component} defaults"):
            selections[component]["uvalue"]["target"] = st.number_input(
                label="Threshold U-Value [W/m²K] - assume no retrofits below this value",
                min_value=float(0),
                value=properties["uvalue"]["target"],
                key=component + "_threshold",
                step=0.05,
            )
            c1, c2 = st.beta_columns(2)
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


@st.cache
def _load_small_area_boundaries(url: str, data_dir: Path) -> gpd.GeoDataFrame:
    return io.load(
        read=gpd.read_parquet, url=url, data_dir=data_dir, filesystem_name="s3"
    )


@st.cache
def _load_buildings(url: str, data_dir: Path):
    return io.load(
        read=pd.read_parquet, url=url, data_dir=data_dir, filesystem_name="s3"
    )


@st.cache
def _filter_buildings(
    buildings: pd.DataFrame, selections: Dict[str, Any]
) -> pd.DataFrame:
    filtered_buildings = (
        buildings.pipe(
            filter.filter_by_substrings,
            column_name="energy_rating",
            selected_substrings=selections["energy_rating"],
            all_substrings=["A", "B", "C", "D", "E", "F", "G"],
        )
        .pipe(
            filter.filter_by_substrings,
            column_name="small_area",
            selected_substrings=selections["small_area"],
            all_substrings=buildings["small_area"],
        )
        .reset_index(drop=True)
    )
    if filtered_buildings.empty:
        raise ValueError(
            f"""
            There are no buildings meeting your criteria:

            energy_rating: {selections["energy_rating"]}

            small_area: {selections["small_area"]}
            """
        )
    else:
        return filtered_buildings


@icontract.ensure(
    lambda pre_vs_post_retrofit_bers: np.array_equal(
        pre_vs_post_retrofit_bers.columns, ["energy_rating", "category", "total"]
    )
)
def _plot_ber_rating_comparison(pre_vs_post_retrofit_bers: pd.DataFrame) -> None:
    chart = (
        alt.Chart(pre_vs_post_retrofit_bers)
        .mark_bar()
        .encode(
            x=alt.X(
                "category",
                axis=alt.Axis(title=None, labels=False, ticks=False),
            ),
            y=alt.Y("total", title="Number of Dwellings"),
            column=alt.Column("energy_rating", title="BER Ratings"),
            color=alt.Color("category"),
        )
        .properties(width=15)  # width of one column facet
    )
    st.altair_chart(chart)


def _plot_retrofit_costs(post_retrofit: pd.DataFrame) -> None:
    cost_columns = [c for c in post_retrofit.columns if "cost" in c]
    costs = (
        post_retrofit[cost_columns]
        .sum()
        .divide(1e6)
        .round(2)
        .rename("M€")
        .reset_index()
    )
    st.write(costs)


if __name__ == "__main__":
    main()
