from pathlib import Path
from typing import Dict, Union

import altair as alt
import numpy as np
import pandas as pd
from rc_building_model import fab
from rc_building_model import htuse
import streamlit as st

data_dir = Path("data")

EXPECTED_COLUMNS = [
    "small_area",
    "year_of_construction",
    "energy_value",
    "roof_area",
    "roof_uvalue",
    "wall_area",
    "wall_uvalue",
    "floor_area",
    "floor_uvalue",
    "window_area",
    "window_uvalue",
    "door_area",
    "door_uvalue",
    "ground_floor_area",
    "first_floor_area",
    "second_floor_area",
    "third_floor_area",
]


def main():
    st.header("Welcome to the Dublin Retrofitting Tool")

    ## Load
    raw_building_stock = fetch_bers()

    with st.form(key="Inputs"):

        st.markdown("> Click `Submit` once you've selected all parameters!")

        ## Filter
        stock_by_ber_rating = filter_by_ber_level(raw_building_stock)
        stock_by_small_area = filter_by_small_area(stock_by_ber_rating)

        ## Initialise
        pre_retrofit_stock = stock_by_small_area.copy()
        post_retrofit_stock = pre_retrofit_stock.copy()

        ## Globals
        total_floor_area = (
            pre_retrofit_stock["ground_floor_area"]
            + pre_retrofit_stock["first_floor_area"]
            + pre_retrofit_stock["second_floor_area"]
            + pre_retrofit_stock["third_floor_area"]
        )

        ## Calculate
        pre_retrofit_fabric_heat_loss = calculate_fabric_heat_loss(pre_retrofit_stock)

        wall_retrofits = retrofit_fabric_component(
            pre_retrofit_stock,
            "wall",
            target_uvalue_default=0.2,
            threshold_uvalue_default=0.5,
            lower_cost_bound_default=50,
            upper_cost_bound_default=300,
            typical_area=70,
        )
        roof_retrofits = retrofit_fabric_component(
            pre_retrofit_stock,
            "roof",
            target_uvalue_default=0.13,
            threshold_uvalue_default=0.5,
            lower_cost_bound_default=5,
            upper_cost_bound_default=30,
            typical_area=50,
        )
        window_retrofits = retrofit_fabric_component(
            pre_retrofit_stock,
            "window",
            target_uvalue_default=0.2,
            threshold_uvalue_default=0.5,
            lower_cost_bound_default=30,
            upper_cost_bound_default=150,
            typical_area=16,
        )
        st.form_submit_button(label="Submit")

    post_retrofit_stock["wall_uvalue"] = wall_retrofits["uvalues"]
    post_retrofit_stock["roof_uvalue"] = roof_retrofits["uvalues"]
    post_retrofit_stock["window_uvalue"] = window_retrofits["uvalues"]
    post_retrofit_fabric_heat_loss = calculate_fabric_heat_loss(post_retrofit_stock)

    energy_value_improvement = (
        pre_retrofit_fabric_heat_loss - post_retrofit_fabric_heat_loss
    ) / total_floor_area
    post_retrofit_stock["energy_value"] = (
        post_retrofit_stock["energy_value"] - energy_value_improvement
    )

    ## Plot
    plot_ber_rating_breakdown(
        pre_retrofit_energy_values=pre_retrofit_stock["energy_value"],
        post_retrofit_energy_values=post_retrofit_stock["energy_value"],
    )
    plot_ber_band_breakdown(
        pre_retrofit_energy_values=pre_retrofit_stock["energy_value"],
        post_retrofit_energy_values=post_retrofit_stock["energy_value"],
    )
    st.subheader("Costs")
    st.markdown(
        "> **Caveat:** The default values for the upper|lower cost estimates are derived"
        " from the [`TABULA`](https://energyaction.ie/projects/tabula.php) project which"
        " ran from 2009 - 2012."
    )
    st.dataframe(
        pd.DataFrame(
            {
                "Lowest Likely Cost [M€]": [
                    wall_retrofits["lower_bound_cost"],
                    roof_retrofits["lower_bound_cost"],
                    window_retrofits["lower_bound_cost"],
                    wall_retrofits["lower_bound_cost"]
                    + roof_retrofits["lower_bound_cost"]
                    + window_retrofits["lower_bound_cost"],
                ],
                "Highest Likely Cost [M€]": [
                    wall_retrofits["upper_bound_cost"],
                    roof_retrofits["upper_bound_cost"],
                    window_retrofits["upper_bound_cost"],
                    wall_retrofits["upper_bound_cost"]
                    + roof_retrofits["upper_bound_cost"]
                    + window_retrofits["upper_bound_cost"],
                ],
            },
            index=["Wall", "Roof", "Window", "Total"],
        )
    )


@st.cache
def fetch_bers():
    bers = pd.read_csv("https://storage.googleapis.com/codema-dev/bers.csv")
    assert set(EXPECTED_COLUMNS).issubset(bers.columns)
    return bers


def _get_ber_rating(energy_values: pd.Series) -> pd.Series:
    return pd.cut(
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


def filter_by_ber_level(building_stock: pd.DataFrame) -> pd.DataFrame:
    building_stock_levels = _get_ber_rating(building_stock["energy_value"]).str[0]
    ber_bands = ["A-B", "C-D", "E-G"]
    options = ["All"] + ber_bands
    selected_ber_rating = st.selectbox(
        "Filter by BER Rating: ",
        options,
    )
    if selected_ber_rating == "All":
        mask = pd.Series([True] * len(building_stock), dtype="bool")
    elif selected_ber_rating in ber_bands:
        if selected_ber_rating == "A-B":
            mask = building_stock_levels.isin(["A", "B"])
        elif selected_ber_rating == "C-D":
            mask = building_stock_levels.isin(["C", "D"])
        else:
            mask = building_stock_levels.isin(["E", "F", "G"])
    else:
        raise ValueError(f"{selected_ber_rating} not in {options}")
    return building_stock[mask].copy()


def calculate_fabric_heat_loss(building_stock: pd.DataFrame) -> pd.Series:
    heat_loss_w_k = fab.calculate_fabric_heat_loss(
        roof_area=building_stock["roof_area"],
        roof_uvalue=building_stock["roof_uvalue"],
        wall_area=building_stock["wall_area"],
        wall_uvalue=building_stock["wall_uvalue"],
        floor_area=building_stock["floor_area"],
        floor_uvalue=building_stock["floor_uvalue"],
        window_area=building_stock["window_area"],
        window_uvalue=building_stock["window_uvalue"],
        door_area=building_stock["door_area"],
        door_uvalue=building_stock["door_uvalue"],
        thermal_bridging_factor=0.05,
    )
    return htuse.calculate_heat_loss_per_year(heat_loss_w_k)


def _select_buildings_to_retrofit(
    original_uvalues: pd.Series,
    percentage_retrofitted: float,
    threshold_uvalue: float,
    random_state: int = 42,
) -> np.array:
    where_uvalue_is_over_threshold = original_uvalues > threshold_uvalue
    to_retrofit = original_uvalues[where_uvalue_is_over_threshold].sample(
        frac=percentage_retrofitted, random_state=random_state
    )
    return original_uvalues.index.isin(to_retrofit.index)


def _retrofit_fabric(
    original_uvalues: pd.Series,
    to_retrofit: pd.Series,
    new_uvalue: float,
) -> pd.Series:
    retrofitted_uvalues = original_uvalues.copy()
    retrofitted_uvalues.loc[to_retrofit] = new_uvalue
    return retrofitted_uvalues


def _estimate_cost_of_fabric_retrofits(
    to_retrofit: pd.Series,
    cost: float,
    areas: pd.Series,
) -> pd.Series:
    return pd.Series([cost] * to_retrofit, dtype="int64") * areas


def retrofit_fabric_component(
    building_stock: pd.DataFrame,
    component: str,
    target_uvalue_default: float,
    threshold_uvalue_default: float,
    lower_cost_bound_default: float,
    upper_cost_bound_default: float,
    typical_area: int,
) -> Dict[str, Union[pd.Series, int]]:
    st.subheader(component.capitalize())

    percentage_retrofitted = (
        st.slider(
            f"% of viable dwellings retrofitted to U-Value = {target_uvalue_default} [W/m²K]",
            min_value=0,
            max_value=100,
            value=0,
            key=component,
        )
        / 100
    )
    with st.beta_expander(label="Change Default Costs & Threshold Values"):
        threshold_uvalue = st.number_input(
            label="Threshold U-Value [W/m²K] - assume no retrofits below this value",
            min_value=float(0),
            value=threshold_uvalue_default,
            key=component,
            step=0.05,
        )
        c1, c2 = st.beta_columns(2)
        lower_bound_cost = c1.number_input(
            label="Lowest* Likely Cost [€/m²]",
            min_value=0,
            value=lower_cost_bound_default,
            key=component,
            step=5,
        )
        upper_bound_cost = c2.number_input(
            label="Highest** Likely Cost [€/m²]",
            min_value=0,
            value=upper_cost_bound_default,
            key=component,
            step=5,
        )
        footnote = (
            f"<small> * {typical_area * lower_bound_cost}€ for a typical {component}"
            f" area of {typical_area}m²<br>"
            f"** {typical_area * upper_bound_cost}€ for a typical {component} area of"
            f" {typical_area}m²</small>"
        )
        st.markdown(footnote, unsafe_allow_html=True)

    buildings_to_retrofit = _select_buildings_to_retrofit(
        original_uvalues=building_stock[f"{component}_uvalue"],
        percentage_retrofitted=percentage_retrofitted,
        threshold_uvalue=threshold_uvalue,
    )
    new_uvalues = _retrofit_fabric(
        original_uvalues=building_stock[f"{component}_uvalue"],
        to_retrofit=buildings_to_retrofit,
        new_uvalue=target_uvalue_default,
    )
    lower_costs = _estimate_cost_of_fabric_retrofits(
        to_retrofit=buildings_to_retrofit,
        cost=lower_bound_cost,
        areas=building_stock[f"{component}_area"],
    )
    upper_costs = _estimate_cost_of_fabric_retrofits(
        to_retrofit=buildings_to_retrofit,
        cost=upper_bound_cost,
        areas=building_stock[f"{component}_area"],
    )

    to_millions = 1e-6
    return {
        "uvalues": new_uvalues,
        "lower_bound_cost": lower_costs.sum() * to_millions,
        "upper_bound_cost": upper_costs.sum() * to_millions,
    }


def _get_ber_rating_breakdown(energy_values: pd.Series):
    return _get_ber_rating(energy_values).astype(str).value_counts().sort_index()


def _get_ber_band_breakdown(energy_values):
    return (
        pd.cut(
            energy_values,
            [
                -np.inf,
                150,
                300,
                np.inf,
            ],
            labels=["A-B", "C-D", "E-G"],
        )
        .astype(str)
        .value_counts()
        .sort_index()
    )


def plot_ber_rating_breakdown(
    pre_retrofit_energy_values: pd.DataFrame, post_retrofit_energy_values: pd.Series
):
    st.subheader("BER Ratings")
    pre_retrofit_ber_ratings = _get_ber_rating_breakdown(pre_retrofit_energy_values)
    post_retrofit_ber_ratings = _get_ber_rating_breakdown(post_retrofit_energy_values)
    ber_ratings = (
        pd.concat(
            [
                pre_retrofit_ber_ratings.to_frame().assign(category="Pre"),
                post_retrofit_ber_ratings.to_frame().assign(category="Post"),
            ]
        )
        .reset_index()
        .rename(columns={"index": "ber_rating", "energy_value": "total"})
    )
    chart = (
        alt.Chart(ber_ratings)
        .mark_bar()
        .encode(
            x=alt.X("category:N", axis=alt.Axis(title=None, labels=False, ticks=False)),
            y=alt.Y("total:Q"),
            column=alt.Column("ber_rating:O"),
            color=alt.Color("category"),
        )
        .properties(width=15)  # width of one column facet
    )
    st.altair_chart(chart)


def plot_ber_band_breakdown(
    pre_retrofit_energy_values: pd.DataFrame, post_retrofit_energy_values: pd.Series
):
    st.subheader("BER Bands")
    pre_retrofit_ber_ratings = _get_ber_band_breakdown(pre_retrofit_energy_values)
    post_retrofit_ber_ratings = _get_ber_band_breakdown(post_retrofit_energy_values)
    ber_ratings = (
        pd.concat(
            [
                pre_retrofit_ber_ratings.to_frame().assign(category="Pre"),
                post_retrofit_ber_ratings.to_frame().assign(category="Post"),
            ]
        )
        .reset_index()
        .rename(columns={"index": "ber_band", "energy_value": "total"})
    )
    chart = (
        alt.Chart(ber_ratings)
        .mark_bar()
        .encode(
            x=alt.X("category:N", axis=alt.Axis(title=None, labels=False, ticks=False)),
            y=alt.Y("total:Q"),
            column=alt.Column("ber_band:O"),
            color=alt.Color("category"),
        )
        .properties(width=125)  # width of one column facet
    )
    st.altair_chart(chart)


if __name__ == "__main__":
    main()
