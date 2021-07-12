import icontract
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

from dea import filter


@pytest.mark.parametrize(
    "bers,selected_postcodes,counties,expected_output",
    [
        (
            pd.DataFrame({"countyname": ["DUBLIN 11", "CO. GALWAY", "CO. CORK"]}),
            ["Dublin 11"],
            ["Dublin", "Galway", "Cork"],
            pd.DataFrame({"countyname": ["DUBLIN 11"]}),
        ),
        (
            pd.DataFrame({"countyname": ["Dublin", "Galway", "Cork"]}),
            ["Dublin", "Galway", "Cork"],
            ["Dublin", "Galway", "Cork"],
            pd.DataFrame(
                {
                    "countyname": ["Dublin", "Galway", "Cork"],
                }
            ),
        ),
    ],
)
def test_filter_by_substrings(
    bers,
    selected_postcodes,
    counties,
    expected_output,
):
    output = filter.filter_by_substrings(
        df=bers,
        column_name="countyname",
        selected_substrings=selected_postcodes,
        all_substrings=counties,
    )
    assert_frame_equal(output, expected_output)


def test_filter_by_substrings_raises_error_if_nan_values():
    bers = pd.DataFrame({"countyname": [np.nan, "CO. GALWAY", "CO. CORK"]})
    selected_substrings = ["Dublin 11"]
    counties = ["Dublin", "Galway", "Cork"]
    with pytest.raises(icontract.ViolationError):
        filter.filter_by_substrings(
            df=bers,
            column_name="countyname",
            selected_substrings=selected_substrings,
            all_substrings=counties,
        )
