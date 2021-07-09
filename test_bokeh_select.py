import geopandas as gpd
import pandas as pd
from pandas.testing import assert_series_equal
from shapely.geometry import Point

import bokeh_select


def test_select_small_areas(monkeypatch):
    def _mock_ask_user_for_small_areas(*args, **kwargs):
        return pd.Series(["1", "2", "3"])

    monkeypatch.setattr(
        "bokeh_select._ask_user_for_small_areas", _mock_ask_user_for_small_areas
    )
    small_area_boundaries = gpd.GeoDataFrame(
        {
            "small_area": ["1", "2", "3"],
            "geometry": [Point(0, 0), Point(0, 1), Point(1, 1)],
        }
    )
    expected_output = pd.Series(["1", "2", "3"])
    output = bokeh_select.select_small_areas(small_area_boundaries)
    assert_series_equal(output, expected_output)
