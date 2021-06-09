import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from dublin_energy_app import archetypes


def _create_index(small_area, index_names):
    return pd.MultiIndex.from_product(
        [[small_area], ["Semi-detached house"], ["1971 - 1980"], [1]],
        names=index_names,
    )


def test_estimate_type_of_wall():
    index_names = ["SMALL_AREA", "dwelling_type", "period_built", "category_id"]
    known_indiv_hh_index = _create_index("000000001", index_names)
    known_indiv_hh = pd.DataFrame(
        {"most_significant_wall_type": ["300mm Filled Cavity"]},
        index=known_indiv_hh_index,
    )
    unknown_indiv_hh_index = _create_index("000000002", index_names)
    unknown_indiv_hh = pd.DataFrame(
        {"most_significant_wall_type": [np.nan]},
        index=unknown_indiv_hh_index,
    )
    wall_archetypes = pd.DataFrame(
        {"most_significant_wall_type": ["Concrete Hollow Block"]},
        index=pd.MultiIndex.from_product(
            [["Semi-detached house"], ["1971 - 1980"]],
            names=["dwelling_type", "period_built"],
        ),
    )
    expected_output = pd.DataFrame(
        {
            "most_significant_wall_type": [
                "300mm Filled Cavity",
                "Concrete Hollow Block",
            ],
            "wall_type_is_estimated": [False, True],
        },
        index=pd.MultiIndex.from_tuples(
            [*known_indiv_hh_index.to_list(), *unknown_indiv_hh_index.to_list()],
            names=index_names,
        ),
    )

    output = archetypes.estimate_type_of_wall(
        known_indiv_hh=known_indiv_hh,
        unknown_indiv_hh=unknown_indiv_hh,
        wall_archetypes=wall_archetypes,
        on=["dwelling_type", "period_built"],
    )

    assert_frame_equal(output, expected_output)


def test_replace_columns_with_other():
    index_names = ["SMALL_AREA", "dwelling_type", "period_built", "category_id"]
    unknown_indiv_hh = pd.DataFrame(
        {
            "most_significant_wall_type": ["Concrete Hollow Block"],
            "wall_uvalue": [np.nan],
        },
        index=pd.MultiIndex.from_product(
            [["000000002"], ["Semi-detached house"], ["1971 - 1980"], [1]],
            names=index_names,
        ),
    )
    wall_uvalue_defaults = pd.DataFrame(
        {
            "wall_uvalue": [2.4],
        },
        index=pd.MultiIndex.from_product(
            [["Concrete Hollow Block"], ["1971 - 1980"]],
            names=["most_significant_wall_type", "period_built"],
        ),
    )
    expected_output = pd.DataFrame(
        {
            "most_significant_wall_type": ["Concrete Hollow Block"],
            "wall_uvalue": [2.4],
        },
        index=pd.MultiIndex.from_product(
            [["000000002"], ["Semi-detached house"], ["1971 - 1980"], [1]],
            names=index_names,
        ),
    )

    output = archetypes._replace_columns_with_other(
        unknown_indiv_hh, wall_uvalue_defaults
    )

    assert_frame_equal(output, expected_output)


def test_estimate_uvalue_of_wall():
    index_names = ["SMALL_AREA", "dwelling_type", "period_built", "category_id"]
    unknown_indiv_hh_index = _create_index("000000002", index_names)
    known_indiv_hh_index = _create_index("000000001", index_names)
    expected_output_index = pd.MultiIndex.from_tuples(
        [*known_indiv_hh_index.to_list(), *unknown_indiv_hh_index.to_list()],
        names=index_names,
    )

    known_indiv_hh = pd.DataFrame(
        {
            "wall_uvalue": [0.3],
            "most_significant_wall_type": ["300mm Filled Cavity"],
        },
        index=known_indiv_hh_index,
    )
    unknown_indiv_hh = pd.DataFrame(
        {
            "wall_uvalue": [np.nan],
            "most_significant_wall_type": [np.nan],
        },
        index=unknown_indiv_hh_index,
    )
    wall_uvalue_defaults = pd.DataFrame(
        {
            "wall_uvalue": [2.4],
        },
        index=pd.MultiIndex.from_product(
            [["Concrete Hollow Block"], ["1971 - 1980"]],
            names=["most_significant_wall_type", "period_built"],
        ),
    )
    wall_types = pd.DataFrame(
        {
            "most_significant_wall_type": [
                "300mm Filled Cavity",
                "Concrete Hollow Block",
            ],
            "wall_type_is_estimated": [False, True],
        },
        index=expected_output_index,
    )
    expected_output = pd.DataFrame(
        {
            "most_significant_wall_type": [
                "300mm Filled Cavity",
                "Concrete Hollow Block",
            ],
            "wall_uvalue": [0.3, 2.4],
            "wall_uvalue_is_estimated": [False, True],
        },
        index=expected_output_index,
    )

    output = archetypes.estimate_uvalue_of_wall(
        known_indiv_hh=known_indiv_hh,
        unknown_indiv_hh=unknown_indiv_hh,
        wall_types=wall_types,
        wall_uvalue_defaults=wall_uvalue_defaults,
    )

    assert_frame_equal(output, expected_output)
