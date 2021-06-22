from pathlib import Path

import numpy as np
import pandas as pd
from rc_building_model import fab
from rc_building_model import htuse
import streamlit as st

data_dir = Path("data")

column_names = {
    "Door Total Area": "door_area",
    "Door Weighted Uvalue": "door_uvalue",
    "Floor Total Area": "floor_area",
    "Floor Weighted Uvalue": "floor_uvalue",
    "No Of Storeys": "no_storeys",
    "Roof Total Area": "roof_area",
    "Roof Weighted Uvalue": "roof_uvalue",
    "Wall Total Area": "wall_area",
    "Wall weighted Uvalue": "wall_uvalue",
    "Windows Total Area": "window_area",
    "WindowsWeighted Uvalue": "window_uvalue",
    "Energy Value": "energy_value",
    "HS Main System Efficiency": "sh_boiler_efficiency",
}


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


known_indiv_hh = (
    pd.read_parquet(data_dir / "ber-dublin.parquet")
    .rename(columns=column_names)
    .reset_index()
)
num_hhs = len(known_indiv_hh)

fabric_heat_loss_pre_retrofit = calculate_fabric_heat_loss(known_indiv_hh)

percentage_retrofitted = (
    st.slider(r"% of homes retrofitted", min_value=0, max_value=100, value=100) / 100
)
number_retrofitted = int(percentage_retrofitted * num_hhs)

retrofitted_hhs = known_indiv_hh.iloc[:number_retrofitted].assign(wall_uvalue=0.13)
unretrofitted_hhs = known_indiv_hh.iloc[number_retrofitted:]
retrofitted_stock = pd.concat([retrofitted_hhs, unretrofitted_hhs]).sort_index()

fabric_heat_loss_post_retrofit = calculate_fabric_heat_loss(retrofitted_stock)
fabric_heat_loss_improvement = (
    fabric_heat_loss_pre_retrofit - fabric_heat_loss_post_retrofit
) / known_indiv_hh["total_floor_area"]

energy_value_post_retrofit = (
    known_indiv_hh["energy_value"] - fabric_heat_loss_improvement
)

ber_ratings_before = pd.cut(
    known_indiv_hh["energy_value"],
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

ber_ratings_after = pd.cut(
    energy_value_post_retrofit,
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

st.subheader("BER Ratings")
c1, c2 = st.beta_columns(2)
c1.write("Before")
c1.write(ber_ratings_before.astype(str).value_counts().sort_index())
c2.write("After")
c2.write(ber_ratings_after.astype(str).value_counts().sort_index())
