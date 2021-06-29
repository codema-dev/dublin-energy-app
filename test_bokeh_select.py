import geopandas as gpd
from geopandas.testing import assert_geodataframe_equal
from shapely.geometry import Point

import bokeh_select


def test_select_small_areas():
    small_area_boundaries = gpd.GeoDataFrame(
        {
            "small_area": ["1", "2", "3"],
            "geometry": [Point(0, 0), Point(0, 1), Point(1, 1)],
        }
    )
    expected_output = small_area_boundaries
    output = bokeh_select.select_small_areas(small_area_boundaries)
    assert_geodataframe_equal(output, expected_output)
