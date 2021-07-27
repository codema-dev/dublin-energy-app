from typing import Any
from typing import Dict

import altair as alt
import icontract
import numpy as np
import pandas as pd
import streamlit as st


@icontract.require(
    lambda pre_vs_post_retrofit_bers: np.array_equal(
        pre_vs_post_retrofit_bers.columns, ["energy_rating", "category", "total"]
    )
)
def plot_ber_rating_comparison(pre_vs_post_retrofit_bers: pd.DataFrame) -> None:
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


@icontract.require(
    lambda pre_vs_post_retrofit_hps: np.array_equal(
        pre_vs_post_retrofit_hps.columns,
        ["is_viable_for_a_heat_pump", "category", "total"],
    )
)
def plot_heat_pump_viability_comparison(pre_vs_post_retrofit_hps: pd.DataFrame) -> None:
    pre_vs_post_retrofit_hps["viability"] = pre_vs_post_retrofit_hps[
        "is_viable_for_a_heat_pump"
    ].astype("string")
    chart = (
        alt.Chart(pre_vs_post_retrofit_hps)
        .mark_bar()
        .encode(
            x=alt.X(
                "category",
                axis=alt.Axis(title=None, labels=False, ticks=False),
            ),
            y=alt.Y("total", title="Number of Dwellings"),
            column=alt.Column("viability", title="Heat Pump Viability"),
            color=alt.Color("category"),
        )
        .properties(width=200)  # width of one column facet
    )
    st.altair_chart(chart)


def plot_retrofit_costs(post_retrofit: pd.DataFrame) -> None:
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
