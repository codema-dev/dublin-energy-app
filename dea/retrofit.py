from typing import Any
from typing import Dict
from typing import List

import icontract
import numpy as np
import pandas as pd
from rcbm import fab
from rcbm import htuse
from rcbm import vent


def _get_viable_buildings(
    uvalues: pd.DataFrame,
    threshold_uvalue: float,
    percentage_selected: float,
    random_seed: int = 42,
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
) -> pd.Series:
    return pd.Series([cost] * is_selected * areas, dtype="int64")


def retrofit_buildings(
    buildings: pd.DataFrame,
    selections: Dict[str, Any],
) -> pd.DataFrame:
    post_retrofit = buildings.copy()
    for component, properties in selections.items():
        where_is_viable_building = _get_viable_buildings(
            uvalues=buildings[component + "_uvalue"],
            threshold_uvalue=properties["uvalue"]["threshold"],
            percentage_selected=properties["percentage_selected"],
        )
        post_retrofit.loc[where_is_viable_building, component + "_uvalue"] = properties[
            "uvalue"
        ]["target"]
        post_retrofit[component + "_cost_lower"] = _estimate_cost_of_fabric_retrofits(
            is_selected=where_is_viable_building,
            cost=properties["cost"]["lower"],
            areas=buildings[component + "_area"],
        )
        post_retrofit[component + "_cost_upper"] = _estimate_cost_of_fabric_retrofits(
            is_selected=where_is_viable_building,
            cost=properties["cost"]["upper"],
            areas=buildings[component + "_area"],
        )
    return calculate_fabric_heat_loss(post_retrofit)


def calculate_fabric_heat_loss(buildings: pd.DataFrame) -> pd.Series:
    buildings["fabric_heat_loss_w_per_k"] = fab.calculate_fabric_heat_loss_coefficient( #in the fab file doenst exist calculate_fabric_heat_loss so replace by calculate_fabric_heat_loss_coefficient 
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
    buildings["fabric_heat_loss_kwh_per_y"] = htuse.calculate_heat_loss_per_year(
        buildings["fabric_heat_loss_w_per_k"]
    )
    return buildings


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
    lambda result, column: np.array_equal(result.columns, [column, "category", "total"])
)
def _get_size_of_pre_vs_post_category(
    pre_retrofit_category: pd.Series, post_retrofit_category: pd.Series, column: str
) -> pd.DataFrame:
    return (
        pd.concat(
            [
                pre_retrofit_category.to_frame().assign(category="Pre"),
                post_retrofit_category.to_frame().assign(category="Post"),
            ]
        )
        .groupby([column, "category"])
        .size()
        .rename("total")
        .reset_index()
    )


def calculate_ber_improvement(
    pre_retrofit: pd.DataFrame, post_retrofit: pd.DataFrame
) -> pd.Series:
    energy_value_improvement = (
        pre_retrofit["fabric_heat_loss_kwh_per_y"]
        - post_retrofit["fabric_heat_loss_kwh_per_y"]
    ) / pre_retrofit["total_floor_area"]
    pre_retrofit_bers = _get_ber_rating(pre_retrofit["energy_value"])
    post_retrofit_bers = _get_ber_rating(
        pre_retrofit["energy_value"] - energy_value_improvement.fillna(0)
    )
    return _get_size_of_pre_vs_post_category(
        pre_retrofit_category=pre_retrofit_bers,
        post_retrofit_category=post_retrofit_bers,
        column="energy_rating",
    )


def _bin_viable_for_heat_pumps(heat_loss_parameter):
    return (
        pd.cut(
            heat_loss_parameter,
            bins=[-np.inf, 2.3, np.inf],
            labels=[True, False],
        )
        .astype(bool)
        .rename("is_viable_for_a_heat_pump")
    )


def calculate_heat_pump_viability_improvement(
    pre_retrofit: pd.DataFrame, post_retrofit: pd.DataFrame
) -> pd.Series:
    pre_retrofit_viability = _bin_viable_for_heat_pumps(
        pre_retrofit["heat_loss_parameter"]
    )
    heat_loss_improvement = (
        pre_retrofit["fabric_heat_loss_w_per_k"]
        - post_retrofit["fabric_heat_loss_w_per_k"]
    )
    post_retrofit_heat_loss_parameter = (
        pre_retrofit["heat_loss_parameter"]
        - heat_loss_improvement / pre_retrofit["total_floor_area"]
    )
    post_retrofit_viability = _bin_viable_for_heat_pumps(
        post_retrofit_heat_loss_parameter
    )
    return _get_size_of_pre_vs_post_category(
        pre_retrofit_category=pre_retrofit_viability,
        post_retrofit_category=post_retrofit_viability,
        column="is_viable_for_a_heat_pump",
    )
