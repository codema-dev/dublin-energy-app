from typing import Any
from typing import Dict
from typing import List

import pandas as pd
import streamlit as st


def _filter_by_substrings(
    df: pd.DataFrame,
    column_name: str,
    selected_substrings: List[str],
    all_substrings: List[str],
) -> pd.DataFrame:
    if len(selected_substrings) == len(all_substrings):
        selected_df = df
    else:
        substrings_to_search = "|".join(selected_substrings)
        selected_df = df[
            df[column_name].str.title().str.contains(substrings_to_search, regex=True)
        ]
    return selected_df


def get_selected_buildings(
    buildings: pd.DataFrame, selections: Dict[str, Any]
) -> pd.DataFrame:
    filtered_buildings = (
        buildings.pipe(
            _filter_by_substrings,
            column_name="energy_rating",
            selected_substrings=selections["energy_rating"],
            all_substrings=["A", "B", "C", "D", "E", "F", "G"],
        )
        .pipe(
            _filter_by_substrings,
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
