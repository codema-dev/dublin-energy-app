from typing import List

import numpy as np
import pandas as pd


def _fill_empty_columns_with_archetypes(
    unknown_indiv_hh: pd.DataFrame,
    archetypes: pd.DataFrame,
) -> pd.DataFrame:
    drop_columns = [
        c for c in archetypes.columns if c in unknown_indiv_hh.reset_index().columns
    ]
    return (
        unknown_indiv_hh.reset_index()
        .drop(columns=drop_columns)
        .set_index(archetypes.index.names)
        .join(archetypes)
        .reset_index()
        .set_index(unknown_indiv_hh.index.names)
    )


def _estimate_type_of_wall(
    known_indiv_hh: pd.DataFrame,
    unknown_indiv_hh: pd.DataFrame,
    wall_type_archetypes: pd.DataFrame,
) -> pd.DataFrame:

    wall_type_is_known = known_indiv_hh["most_significant_wall_type"].notnull()
    unknown_wall_types = pd.concat(
        [
            known_indiv_hh[~wall_type_is_known]["most_significant_wall_type"],
            unknown_indiv_hh["most_significant_wall_type"],
        ]
    )
    estimated_wall_types = _fill_empty_columns_with_archetypes(
        unknown_wall_types, wall_type_archetypes
    )
    return pd.concat(
        [
            known_indiv_hh[wall_type_is_known][
                ["wall_uvalue", "most_significant_wall_type"]
            ].assign(wall_type_is_estimated=False),
            estimated_wall_types.assign(
                wall_type_is_estimated=True, wall_uvalue=np.nan
            ),
        ]
    )


def _estimate_uvalue_of_wall(
    wall_types: pd.DataFrame,
    wall_uvalue_defaults: pd.DataFrame,
) -> pd.DataFrame:
    wall_uvalue_is_estimated = wall_types["wall_uvalue"].isnull()
    known_wall_uvalues = wall_types[~wall_uvalue_is_estimated]
    unknown_wall_uvalues = wall_types[wall_uvalue_is_estimated]

    estimated_wall_uvalues = _fill_empty_columns_with_archetypes(
        unknown_wall_uvalues, wall_uvalue_defaults
    )
    return pd.concat(
        [
            known_wall_uvalues.assign(wall_uvalue_is_estimated=False),
            estimated_wall_uvalues.assign(wall_uvalue_is_estimated=True),
        ]
    )


def estimate_wall_properties(
    known_indiv_hh: pd.DataFrame,
    unknown_indiv_hh: pd.DataFrame,
    wall_type_archetypes: pd.DataFrame,
    wall_uvalue_defaults: pd.DataFrame,
):
    wall_types = _estimate_type_of_wall(
        known_indiv_hh=known_indiv_hh,
        unknown_indiv_hh=unknown_indiv_hh,
        wall_type_archetypes=wall_type_archetypes,
    )
    return _estimate_uvalue_of_wall(
        wall_types=wall_types, wall_uvalue_defaults=wall_uvalue_defaults
    )