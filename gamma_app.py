from pathlib import Path
from urllib.request import urlretrieve

import numpy as np
import pandas as pd
from rc_building_model import fab
from rc_building_model import htuse
import streamlit as st

data_dir = Path("data")


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


def retrofit_fabric(
    percentage_retrofitted: float,
    total_number_of_hhs: int,
    new_uvalue: float,
    original_uvalues: pd.Series,
) -> pd.Series:
    number_retrofitted = int(percentage_retrofitted * total_number_of_hhs)
    retrofitted_uvalues = pd.Series([new_uvalue] * number_retrofitted)
    unretrofitted_uvalues = original_uvalues.iloc[number_retrofitted:]
    return pd.concat([retrofitted_uvalues, unretrofitted_uvalues])


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


def assign_ber_bandas(energy_ratings):
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


@st.cache
def load_data():
    return pd.read_csv("data/dublin_small_area_bers.csv")


## Load Data

pre_retrofitted_stock = load_data()
retrofitted_stock = pre_retrofitted_stock.copy()
total_number_of_hhs = len(pre_retrofitted_stock)

total_floor_area = (
    pre_retrofitted_stock["ground_floor_area"]
    + pre_retrofitted_stock["first_floor_area"]
    + pre_retrofitted_stock["second_floor_area"]
    + pre_retrofitted_stock["third_floor_area"]
)

## Calculate Retrofit BER Impact

fabric_heat_loss_pre_retrofit = calculate_fabric_heat_loss(pre_retrofitted_stock)

percentage_walls_retrofitted = (
    st.slider(r"% of Walls retrofitted", min_value=0, max_value=100, value=50) / 100
)
retrofitted_stock["wall_uvalue"] = retrofit_fabric(
    percentage_retrofitted=percentage_walls_retrofitted,
    total_number_of_hhs=total_number_of_hhs,
    new_uvalue=0.2,
    original_uvalues=pre_retrofitted_stock["wall_uvalue"],
)

percentage_roofs_retrofitted = (
    st.slider(r"% of Roofs retrofitted", min_value=0, max_value=100, value=0) / 100
)
retrofitted_stock["roof_uvalue"] = retrofit_fabric(
    percentage_retrofitted=percentage_roofs_retrofitted,
    total_number_of_hhs=total_number_of_hhs,
    new_uvalue=0.13,
    original_uvalues=pre_retrofitted_stock["roof_uvalue"],
)

percentage_windows_doors_retrofitted = (
    st.slider(r"% of Windows|Doors retrofitted", min_value=0, max_value=100, value=0)
    / 100
)
retrofitted_stock["window_uvalue"] = retrofit_fabric(
    percentage_retrofitted=percentage_windows_doors_retrofitted,
    total_number_of_hhs=total_number_of_hhs,
    new_uvalue=0.9,
    original_uvalues=pre_retrofitted_stock["window_uvalue"],
)
retrofitted_stock["door_uvalue"] = retrofit_fabric(
    percentage_retrofitted=percentage_windows_doors_retrofitted,
    total_number_of_hhs=total_number_of_hhs,
    new_uvalue=2,
    original_uvalues=pre_retrofitted_stock["door_uvalue"],
)

fabric_heat_loss_post_retrofit = calculate_fabric_heat_loss(retrofitted_stock)

fabric_heat_loss_improvement = (
    fabric_heat_loss_pre_retrofit - fabric_heat_loss_post_retrofit
) / total_floor_area

retrofitted_energy_values = (
    pre_retrofitted_stock["energy_value"] - fabric_heat_loss_improvement
)

ber_ratings_before = assign_ber_ratings(
    pre_retrofitted_stock["energy_value"].rename("total")
)
ber_ratings_after = assign_ber_ratings(retrofitted_energy_values.rename("total"))

st.subheader("BER Ratings")
c1, c2, c3, c4 = st.beta_columns(4)
c1.write("Before")
c1.write(ber_ratings_before.astype(str).value_counts().sort_index())
c2.write(
    ber_ratings_before.pipe(assign_ber_bandas).astype(str).value_counts().sort_index()
)
c3.write("After")
c3.write(ber_ratings_after.astype(str).value_counts().sort_index())
c4.write(
    ber_ratings_after.pipe(assign_ber_bandas).astype(str).value_counts().sort_index()
)
