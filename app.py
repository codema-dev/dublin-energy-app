from collections import defaultdict
from configparser import ConfigParser
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List

import altair as alt
import geopandas as gpd
import icontract
import numpy as np
import pandas as pd
from rcbm import fab
from rcbm import htuse
import streamlit as st
from streamlit.state.session_state import Value

from dea import filter
from dea import io
from dea.mapselect import mapselect
from dea import CONFIG
from dea import DEFAULTS
from dea import _DATA_DIR

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
            retrofitted_buildings = _retrofit_buildings(
                buildings=filtered_buildings, selections=selections
            )

        with st.spinner("Calculating BER improvement..."):
            pre_vs_post_retrofit_bers = _calculate_ber_improvement(
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
    # Remove NS or Not stated buildings until ibsg can replace them with SA modes
    return io.load(
        read=pd.read_parquet, url=url, data_dir=data_dir, filesystem_name="s3"
    ).assign(energy_rating=lambda df: _get_ber_rating(df["energy_value"]))


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


def _get_viable_buildings(
    uvalues: pd.DataFrame,
    threshold_uvalue: float,
    percentage_selected: float,
    random_seed: float,
) -> pd.Series:
    where_uvalue_is_over_threshold = uvalues > threshold_uvalue
    subset_over_threshold = uvalues[where_uvalue_is_over_threshold].sample(
        frac=percentage_selected, random_state=random_seed
    )
    return uvalues.index.isin(subset_over_threshold.index)


def _estimate_cost_of_fabric_retrofits(
    is_selected: pd.Series,
    cost: float,
    areas: pd.Series,
    name: str,
) -> pd.Series:
    return pd.Series([cost] * is_selected * areas, dtype="int64", name=name)


def _retrofit_buildings(
    buildings: pd.DataFrame, selections: Dict[str, Any], random_seed: float = 42
) -> pd.DataFrame:
    retofitted_properties: List[pd.Series] = []
    all_columns_but_uvalues: List[str] = list(buildings.columns)
    for component, properties in selections["retrofit"].items():
        column_name = component + "_uvalue"
        uvalues = buildings[column_name].copy()
        where_is_viable_building = _get_viable_buildings(
            uvalues=uvalues,
            threshold_uvalue=properties["uvalue"]["threshold"],
            percentage_selected=properties["percentage_selected"],
            random_seed=random_seed,
        )
        uvalues.loc[where_is_viable_building] = properties["uvalue"]["target"]
        retrofitted_uvalues = uvalues
        areas = buildings[component + "_area"]
        cost_lower = _estimate_cost_of_fabric_retrofits(
            is_selected=where_is_viable_building,
            cost=properties["cost"]["lower"],
            areas=areas,
            name=component + "_cost_lower",
        )
        cost_upper = _estimate_cost_of_fabric_retrofits(
            is_selected=where_is_viable_building,
            cost=properties["cost"]["upper"],
            areas=areas,
            name=component + "_cost_upper",
        )
        all_columns_but_uvalues.remove(column_name)
        retofitted_properties += [retrofitted_uvalues, cost_lower, cost_upper]
    retrofits = pd.concat(retofitted_properties, axis="columns")
    return pd.concat(
        [buildings[all_columns_but_uvalues], retrofits],
        axis="columns",
    )


def _calculate_fabric_heat_loss(buildings: pd.DataFrame) -> pd.Series:
    heat_loss_w_k = fab.calculate_fabric_heat_loss(
        roof_area=buildings["roof_area"],
        roof_uvalue=buildings["roof_uvalue"],
        wall_area=buildings["wall_area"],
        wall_uvalue=buildings["wall_uvalue"],
        floor_area=buildings["floor_area"],
        floor_uvalue=buildings["floor_uvalue"],
        window_area=buildings["window_area"],
        window_uvalue=buildings["window_uvalue"],
        door_area=buildings["door_area"],
        door_uvalue=buildings["door_uvalue"],
        thermal_bridging_factor=0.05,
    )
    return htuse.calculate_heat_loss_per_year(heat_loss_w_k)


def _get_ber_rating(energy_values: pd.Series) -> pd.Series:
    return (
        pd.cut(
            energy_values,
            [
                -np.inf,
                25,
                50,
                75,
                100,
                125,
                150,
                175,
                200,
                225,
                260,
                300,
                340,
                380,
                450,
                np.inf,
            ],
            labels=[
                "A1",
                "A2",
                "A3",
                "B1",
                "B2",
                "B3",
                "C1",
                "C2",
                "C3",
                "D1",
                "D2",
                "E1",
                "E2",
                "F",
                "G",
            ],
        )
        .rename("energy_rating")
        .astype("string")
    )  # streamlit & altair don't recognise category


@icontract.ensure(
    lambda result: np.array_equal(
        result.columns, ["energy_rating", "category", "total"]
    )
)
def _combine_pre_and_post_bers(
    pre_retrofit_bers: pd.Series, post_retrofit_bers: pd.Series
) -> pd.DataFrame:
    return (
        pd.concat(
            [
                pre_retrofit_bers.to_frame().assign(category="Pre"),
                post_retrofit_bers.to_frame().assign(category="Post"),
            ]
        )
        .groupby(["energy_rating", "category"])
        .size()
        .rename("total")
        .reset_index()
    )


def _calculate_ber_improvement(
    pre_retrofit: pd.DataFrame, post_retrofit: pd.DataFrame
) -> pd.Series:
    total_floor_area = (
        pre_retrofit["ground_floor_area"]
        + pre_retrofit["first_floor_area"]
        + pre_retrofit["second_floor_area"]
        + pre_retrofit["third_floor_area"]
    )
    pre_retrofit_fabric_heat_loss = _calculate_fabric_heat_loss(pre_retrofit)
    post_retrofit_fabric_heat_loss = _calculate_fabric_heat_loss(post_retrofit)
    energy_value_improvement = (
        pre_retrofit_fabric_heat_loss - post_retrofit_fabric_heat_loss
    ) / total_floor_area
    post_retrofit_bers = _get_ber_rating(
        pre_retrofit["energy_value"] - energy_value_improvement.fillna(0)
    )
    return _combine_pre_and_post_bers(
        pre_retrofit_bers=pre_retrofit["energy_rating"],
        post_retrofit_bers=post_retrofit_bers,
    )


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
