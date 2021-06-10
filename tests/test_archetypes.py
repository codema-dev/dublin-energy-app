import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

from dublin_energy_app import archetypes


@pytest.fixture
def known_indiv_hh() -> pd.DataFrame:
    return pd.DataFrame(
        {"most_significant_wall_type": ["300mm filled cavity"], "wall_uvalue": [0.3]},
        index=pd.MultiIndex.from_product(
            [["000000001"], ["Semi-detached house"], ["1971 - 1980"], [1]],
            names=["SMALL_AREA", "dwelling_type", "period_built", "category_id"],
        ),
    )


@pytest.fixture
def unknown_indiv_hh() -> pd.DataFrame:
    return pd.DataFrame(
        {"most_significant_wall_type": [np.nan], "wall_uvalue": [np.nan]},
        index=pd.MultiIndex.from_product(
            [["000000002"], ["Semi-detached house"], ["1971 - 1980"], [1]],
            names=["SMALL_AREA", "dwelling_type", "period_built", "category_id"],
        ),
    )


@pytest.fixture
def wall_uvalue_defaults() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "wall_uvalue": [2.4],
        },
        index=pd.MultiIndex.from_product(
            [["concrete hollow block"], ["1971 - 1980"]],
            names=["most_significant_wall_type", "period_built"],
        ),
    )


@pytest.fixture
def wall_type_archetypes() -> pd.DataFrame:
    return pd.DataFrame(
        {"most_significant_wall_type": ["concrete hollow block"]},
        index=pd.MultiIndex.from_product(
            [["Semi-detached house"], ["1971 - 1980"]],
            names=["dwelling_type", "period_built"],
        ),
    )


def test_fill_empty_columns_with_archetypes(unknown_indiv_hh, wall_type_archetypes):
    expected_output = pd.DataFrame(
        {
            "most_significant_wall_type": ["concrete hollow block"],
            "wall_uvalue": [np.nan],
        },
        index=unknown_indiv_hh.index,
    )

    output = archetypes._fill_empty_columns_with_archetypes(
        unknown_indiv_hh, wall_type_archetypes
    )

    assert_frame_equal(output, expected_output, check_like=True)


def test_estimate_type_of_wall(known_indiv_hh, unknown_indiv_hh, wall_type_archetypes):
    expected_output = pd.DataFrame(
        {
            "most_significant_wall_type": [
                "300mm filled cavity",
                "concrete hollow block",
            ],
            "wall_type_is_estimated": [False, True],
            "wall_uvalue": [0.3, np.nan],
        },
        index=pd.MultiIndex.from_arrays(
            [
                ["000000001", "000000002"],
                ["Semi-detached house", "Semi-detached house"],
                ["1971 - 1980", "1971 - 1980"],
                [1, 1],
            ],
            names=["SMALL_AREA", "dwelling_type", "period_built", "category_id"],
        ),
    )

    output = archetypes._estimate_type_of_wall(
        known_indiv_hh=known_indiv_hh,
        unknown_indiv_hh=unknown_indiv_hh,
        wall_type_archetypes=wall_type_archetypes,
    )

    assert_frame_equal(output, expected_output, check_like=True)


def test_estimate_uvalue_of_wall(wall_uvalue_defaults):
    wall_types = pd.DataFrame(
        {
            "most_significant_wall_type": [
                "concrete hollow block",
                "300mm filled cavity",
            ],
            "wall_type_is_estimated": [True, False],
            "wall_uvalue": [np.nan, 0.3],
        },
        index=pd.MultiIndex.from_arrays(
            [
                ["000000001", "000000002"],
                ["Semi-detached house", "Semi-detached house"],
                ["1971 - 1980", "1971 - 1980"],
                [1, 1],
            ],
            names=["SMALL_AREA", "dwelling_type", "period_built", "category_id"],
        ),
    )
    expected_output = pd.DataFrame(
        {
            "most_significant_wall_type": [
                "concrete hollow block",
                "300mm filled cavity",
            ],
            "wall_type_is_estimated": [True, False],
            "wall_uvalue": [2.4, 0.3],
            "wall_uvalue_is_estimated": [True, False],
        },
        index=pd.MultiIndex.from_arrays(
            [
                ["000000001", "000000002"],
                ["Semi-detached house", "Semi-detached house"],
                ["1971 - 1980", "1971 - 1980"],
                [1, 1],
            ],
            names=["SMALL_AREA", "dwelling_type", "period_built", "category_id"],
        ),
    )

    output = archetypes._estimate_uvalue_of_wall(
        wall_types=wall_types,
        wall_uvalue_defaults=wall_uvalue_defaults,
    )

    assert_frame_equal(output, expected_output, check_like=True)


def test_estimate_wall_properties(
    known_indiv_hh, unknown_indiv_hh, wall_type_archetypes, wall_uvalue_defaults
):
    expected_output = pd.DataFrame(
        {
            "most_significant_wall_type": [
                "300mm filled cavity",
                "concrete hollow block",
            ],
            "wall_type_is_estimated": [False, True],
            "wall_uvalue": [0.3, 2.4],
            "wall_uvalue_is_estimated": [False, True],
        },
        index=pd.MultiIndex.from_arrays(
            [
                ["000000001", "000000002"],
                ["Semi-detached house", "Semi-detached house"],
                ["1971 - 1980", "1971 - 1980"],
                [1, 1],
            ],
            names=["SMALL_AREA", "dwelling_type", "period_built", "category_id"],
        ),
    )

    output = archetypes.estimate_wall_properties(
        known_indiv_hh=known_indiv_hh,
        unknown_indiv_hh=unknown_indiv_hh,
        wall_type_archetypes=wall_type_archetypes,
        wall_uvalue_defaults=wall_uvalue_defaults,
    )

    assert_frame_equal(output, expected_output, check_like=True)
