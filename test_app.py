import numpy as np
from numpy.testing import assert_array_almost_equal
import pandas as pd
from pandas.testing import assert_frame_equal
from pandas.testing import assert_series_equal
import pytest

import app


@pytest.mark.parametrize(
    "selected_ber,expected_output",
    [
        ("All", pd.DataFrame({"energy_value": [50, 200, 600]})),
        ("A-B", pd.DataFrame({"energy_value": [50]}, index=[0])),
        ("C-D", pd.DataFrame({"energy_value": [200]}, index=[1])),
        ("E-G", pd.DataFrame({"energy_value": [600]}, index=[2])),
    ],
)
def test_filter_by_ber_level(selected_ber, expected_output, monkeypatch):
    def _mock_selectbox(*args, **kwargs):
        return selected_ber

    monkeypatch.setattr("app.st.selectbox", _mock_selectbox)
    building_stock = pd.DataFrame({"energy_value": [50, 200, 600]})
    output = app.filter_by_ber_level(building_stock)
    assert_frame_equal(output, expected_output)


def test_select_buildings_to_retrofit():
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
    output = app._select_buildings_to_retrofit(
        original_uvalues=original_uvalues,
        percentage_retrofitted=percentage_retrofitted,
        threshold_uvalue=threshold_uvalue,
        random_state=random_state,
    )
    assert_array_almost_equal(output, expected_output)


def test_retrofit_fabric():
    original_uvalues = pd.Series([0.13, 2.3, 0.13, 2.3], dtype="float64")
    to_retrofit = pd.Series([False, True, False, False], dtype="bool")
    new_uvalue = 0.13
    expected_output = pd.Series([0.13, 0.13, 0.13, 2.3])
    output = app._retrofit_fabric(
        original_uvalues=original_uvalues,
        to_retrofit=to_retrofit,
        new_uvalue=new_uvalue,
    )
    assert_series_equal(output, expected_output)


def test_estimate_cost_of_fabric_retrofits():
    to_retrofit = pd.Series([False, True, False, False], dtype="bool")
    cost = 100
    floor_areas = pd.Series([100] * 4, dtype="int64")
    expected_output = pd.Series([0, 10000, 0, 0])
    output = app._estimate_cost_of_fabric_retrofits(
        to_retrofit=to_retrofit, cost=cost, floor_areas=floor_areas
    )
    assert_series_equal(output, expected_output)
