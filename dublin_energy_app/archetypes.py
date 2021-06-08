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


def estimate_uvalue_of_wall(
    known_indiv_hh: pd.DataFrame,
    unknown_indiv_hh: pd.DataFrame,
    wall_archetypes: pd.DataFrame,
) -> pd.DataFrame:
    estimated_indiv_hh = (
        unknown_indiv_hh.reset_index()
        .set_index(wall_archetypes.index.names)
        .drop(columns="Wall weighted Uvalue")
        .join(wall_archetypes)
        .reset_index()
        .set_index(known_indiv_hh.index.names)
    )
    on_columns = ["most_significant_wall_type", "Wall weighted Uvalue"]
    return pd.concat(
        [
            known_indiv_hh[on_columns].assign(wall_uvalue_is_estimated=False),
            estimated_indiv_hh[on_columns].assign(wall_uvalue_is_estimated=True),
        ]
    )
