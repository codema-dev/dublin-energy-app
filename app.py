from pathlib import Path
from typing import Dict
from urllib.request import urlretrieve

import numpy as np
import pandas as pd
from rc_building_model import fab
from rc_building_model import htuse
import streamlit as st

data_dir = Path("data")

EXPECTED_COLUMNS = [
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
    pre_retrofitted_stock = fetch_bers()
    retrofitted_stock = pre_retrofitted_stock.copy()
    pre_retrofit_fabric_heat_loss = calculate_fabric_heat_loss(pre_retrofitted_stock)
    wall_retrofits = retrofit_fabric_component(
        pre_retrofitted_stock,
        "wall",
        target_uvalue_default=0.2,
        lower_cost_bound_default=50,
        upper_cost_bound_default=300,
    )
    roof_retrofits = retrofit_fabric_component(
        pre_retrofitted_stock,
        "roof",
        target_uvalue_default=0.13,
        lower_cost_bound_default=5,
        upper_cost_bound_default=30,
    )
    window_retrofits = retrofit_fabric_component(
        pre_retrofitted_stock,
        "window",
        target_uvalue_default=0.2,
        lower_cost_bound_default=30,
        upper_cost_bound_default=150,
    )


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


def assign_ber_ratings(energy_values: pd.Series):
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


def assign_ber_bands(energy_ratings):
    return energy_ratings.str[0].map(
        {
            "A": "A-B",
            "B": "A-B",
            "C": "C-D",
            "D": "C-D",
            "E": "E-G",
            "F": "E-G",
            "G": "E-G",
        }
    )


def _fetch(url: str, filepath: Path):
    if not filepath.exists():
        urlretrieve(url=url, filename=filepath)


@st.cache
def fetch_bers():
    filepath = Path("bers.csv")
    _fetch(url="https://storage.googleapis.com/codema-dev/bers.csv", filepath=filepath)
    bers = pd.read_csv(filepath)
    assert set(EXPECTED_COLUMNS).issubset(bers.columns)
    return bers


def _retrofit_fabric(
    percentage_retrofitted: float,
    sample_size: int,
    new_uvalue: float,
    original_uvalues: pd.Series,
) -> pd.Series:
    number_retrofitted = int(percentage_retrofitted * sample_size)
    retrofitted_uvalues = pd.Series([new_uvalue] * number_retrofitted)
    unretrofitted_uvalues = original_uvalues.iloc[number_retrofitted:]
    return pd.concat([retrofitted_uvalues, unretrofitted_uvalues]).reset_index(
        drop=True
    )


def _estimate_cost_of_fabric_retrofits(
    percentage_retrofitted: float,
    sample_size: int,
    cost: float,
    floor_areas: pd.Series,
) -> pd.Series:
    number_retrofitted = int(percentage_retrofitted * sample_size)
    number_unretrofitted = sample_size - number_retrofitted
    retrofit_cost = pd.Series([cost] * number_retrofitted)
    unretrofitted_cost = pd.Series([0] * number_unretrofitted)
    return (
        pd.concat([retrofit_cost, unretrofitted_cost]).reset_index(drop=True)
        * floor_areas
    )


def retrofit_fabric_component(
    building_stock: pd.DataFrame,
    component: str,
    target_uvalue_default: float,
    lower_cost_bound_default: float,
    upper_cost_bound_default: float,
):
    st.subheader(component.capitalize())

    percentage_retrofitted = (
        st.slider(
            f"% of dwellings retrofitted to {target_uvalue_default} [kWh/m²year]",
            min_value=0,
            max_value=100,
            value=0,
            key=component,
        )
        / 100
    )

    c1, c2 = st.beta_columns(2)
    lower_bound_cost = c1.number_input(
        label="Lowest Likely Cost [€/m²]",
        min_value=0,
        value=lower_cost_bound_default,
        key=component,
        step=5,
    )
    upper_bound_cost = c2.number_input(
        label="Highest Likely Cost [€/m²]",
        min_value=0,
        value=upper_cost_bound_default,
        key=component,
        step=5,
    )

    size_of_stock = len(building_stock)
    total_floor_area = (
        building_stock["ground_floor_area"]
        + building_stock["first_floor_area"]
        + building_stock["second_floor_area"]
        + building_stock["third_floor_area"]
    )

    new_uvalues = _retrofit_fabric(
        percentage_retrofitted=percentage_retrofitted,
        sample_size=size_of_stock,
        new_uvalue=target_uvalue_default,
        original_uvalues=building_stock[f"{component}_uvalue"],
    )

    lower_costs = _estimate_cost_of_fabric_retrofits(
        percentage_retrofitted=percentage_retrofitted,
        sample_size=size_of_stock,
        cost=lower_bound_cost,
        floor_areas=total_floor_area,
    )
    upper_costs = _estimate_cost_of_fabric_retrofits(
        percentage_retrofitted=percentage_retrofitted,
        sample_size=size_of_stock,
        cost=upper_bound_cost,
        floor_areas=total_floor_area,
    )

    return {
        "uvalues": new_uvalues,
        "lower_costs": lower_costs,
        "upper_costs": upper_costs,
    }


if __name__ == "__main__":
    main()
