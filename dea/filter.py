from typing import List

import icontract
import pandas as pd
import streamlit as st


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
