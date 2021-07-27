from typing import Any
from typing import Dict
from typing import List

import icontract
import numpy as np
import pandas as pd
from rcbm import fab
from rcbm import htuse


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


def retrofit_buildings(
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


def calculate_ber_improvement(
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
    pre_retrofit_bers = _get_ber_rating(pre_retrofit["energy_value"])
    post_retrofit_bers = _get_ber_rating(
        pre_retrofit["energy_value"] - energy_value_improvement.fillna(0)
    )
    return _combine_pre_and_post_bers(
        pre_retrofit_bers=pre_retrofit_bers,
        post_retrofit_bers=post_retrofit_bers,
    )
