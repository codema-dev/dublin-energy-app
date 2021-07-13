import numpy as np
from numpy.testing import assert_array_almost_equal
import pandas as pd
from pandas.testing import assert_series_equal
from pandas.testing import assert_frame_equal

import app


def test_get_viable_buildings():
    original_uvalues = pd.Series([0.13, 2.3] * 6, dtype="float16")
    percentage_retrofitted = 0.5
    threshold_uvalue = 0.5
    random_state = 42
    expected_output = np.array(
        [
            False,
            True,
            False,
            True,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            True,
        ],
        dtype="bool",
    )
    output = app._get_viable_buildings(
        uvalues=original_uvalues,
        threshold_uvalue=threshold_uvalue,
        percentage_selected=percentage_retrofitted,
        random_seed=42,
    )
    assert_array_almost_equal(output, expected_output)


def test_estimate_cost_of_fabric_retrofits():
    to_retrofit = pd.Series([False, True, False, False], dtype="bool")
    cost = 100
    wall_areas = pd.Series([100] * 4, dtype="int64")
    expected_output = pd.Series([0, 10000, 0, 0])
    output = app._estimate_cost_of_fabric_retrofits(
        is_selected=to_retrofit, cost=cost, areas=wall_areas, name=None
    )
    assert_series_equal(output, expected_output)


def test_retrofit_buildings():
    buildings = pd.DataFrame(
        {
            "wall_uvalue": [0.1, 2, 2],
            "wall_area": [50, 150, 100],
            "roof_uvalue": [0.1, 2, 2],
            "roof_area": [50, 150, 100],
            "floor_uvalue": [0.1, 2, 2],
            "floor_area": [0.1, 2, 2],
        }
    )
    selections = {
        "retrofit": {
            "wall": {
                "uvalue": {
                    "threshold": 0.2,
                    "target": 0.5,
                },
                "percentage_selected": 0.5,
                "cost": {
                    "lower": 50,
                    "upper": 300,
                },
            },
            "roof": {
                "uvalue": {
                    "threshold": 0.2,
                    "target": 0.5,
                },
                "percentage_selected": 0.5,
                "cost": {
                    "lower": 50,
                    "upper": 300,
                },
            },
        }
    }
    expected_output = pd.DataFrame(
        {
            "floor_uvalue": [0.1, 2, 2],
            "floor_area": [0.1, 2, 2],
            "wall_area": [50, 150, 100],
            "roof_area": [50, 150, 100],
            "wall_uvalue": [0.1, 2, 0.5],
            "wall_cost_lower": [0, 0, 5000],
            "wall_cost_upper": [0, 0, 30000],
            "roof_uvalue": [0.1, 2, 0.5],
            "roof_cost_lower": [0, 0, 5000],
            "roof_cost_upper": [0, 0, 30000],
        }
    )
    output = app._retrofit_buildings(
        buildings=buildings, selections=selections, random_seed=42
    )
    assert_frame_equal(output, expected_output, check_like=True)
