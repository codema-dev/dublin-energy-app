from numpy import exp
import pandas as pd
from pandas.testing import assert_frame_equal
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
