from typing import List

import icontract
import pandas as pd
import streamlit as st


@icontract.ensure(lambda result: len(result) > 0)
@icontract.require(
    lambda df, column_name: ~df[column_name].isnull().any(),
    error=lambda column_name, selected_substrings: icontract.ViolationError(
        f"Cannot filter {column_name} on {selected_substrings} as it contains NA / NaN values"
    ),
)
def filter_by_substrings(
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
