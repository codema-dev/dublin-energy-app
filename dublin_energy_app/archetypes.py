from typing import List

import pandas as pd


def estimate_type_of_wall(
    known_indiv_hh: pd.DataFrame,
    unknown_indiv_hh: pd.DataFrame,
    wall_archetypes: pd.DataFrame,
    on: List[str],
) -> pd.DataFrame:
    wall_type_is_known = known_indiv_hh["most_significant_wall_type"].notnull()
    unknown_wall_types = pd.concat(
        [
            known_indiv_hh[~wall_type_is_known]["most_significant_wall_type"],
            unknown_indiv_hh["most_significant_wall_type"],
        ]
    )
    estimated_wall_types = (
        unknown_wall_types.reset_index()
        .set_index(on)
        .combine_first(wall_archetypes)
        .reset_index()
        .set_index(known_indiv_hh.index.names)
    )
    return pd.concat(
        [
            known_indiv_hh[wall_type_is_known][["most_significant_wall_type"]].assign(
                wall_type_is_estimated=False
            ),
            estimated_wall_types.assign(wall_type_is_estimated=True),
        ]
    )


def _replace_columns_with_other(
    unknown_indiv_hh: pd.DataFrame,
    estimates: pd.DataFrame,
) -> pd.DataFrame:
    drop_columns = [
        c for c in estimates.columns if c in unknown_indiv_hh.reset_index().columns
    ]
    return (
        unknown_indiv_hh.reset_index()
        .drop(columns=drop_columns)
        .set_index(estimates.index.names)
        .join(estimates)
        .reset_index()
        .set_index(unknown_indiv_hh.index.names)
    )


def estimate_uvalue_of_wall(
    known_indiv_hh: pd.DataFrame,
    unknown_indiv_hh: pd.DataFrame,
    wall_types: pd.DataFrame,
    wall_uvalue_defaults: pd.DataFrame,
) -> pd.DataFrame:
    estimated_indiv_hh_with_wall_types = _replace_columns_with_other(
        unknown_indiv_hh, wall_types
    )
    estimated_indiv_hh = _replace_columns_with_other(
        estimated_indiv_hh_with_wall_types, wall_uvalue_defaults
    )

    on_columns = ["most_significant_wall_type", "wall_uvalue"]
    return pd.concat(
        [
            known_indiv_hh[on_columns].assign(wall_uvalue_is_estimated=False),
            estimated_indiv_hh[on_columns].assign(wall_uvalue_is_estimated=True),
        ]
    )
