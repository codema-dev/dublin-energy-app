import json
from typing import List

from bokeh.models.plots import Plot
from bokeh.plotting import figure
from bokeh.plotting import Figure
from bokeh.models import ColumnDataSource, CustomJS, GeoJSONDataSource
from bokeh.tile_providers import CARTODBPOSITRON, get_provider

import geopandas as gpd
import pandas as pd
import streamlit as st
from streamlit_bokeh_events import streamlit_bokeh_events


@st.cache
def load_small_area_boundaries() -> gpd.GeoDataFrame:
    # CARTODBPOSITRON tile requires this crs
    return gpd.read_file(
        "data/dublin_small_area_boundaries_2016",
    ).to_crs(epsg="3857")


@st.cache
def _convert_geometry_to_xy(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return gdf.assign(
        x=lambda gdf: gdf.geometry.centroid.x, y=lambda gdf: gdf.geometry.centroid.y
    ).drop(columns="geometry")


@st.cache
def _convert_to_geojson_str(gdf: gpd.GeoDataFrame) -> str:
    return json.dumps(json.loads(small_area_boundaries.to_crs(epsg="3857").to_json()))


def _plot_basemap(boundaries: str):
    gds_polygons = GeoJSONDataSource(geojson=boundaries)
    plot = figure(
        tools="pan, zoom_in, zoom_out, box_zoom, wheel_zoom, lasso_select",
        width=500,
        height=500,
    )
    tile_provider = get_provider(CARTODBPOSITRON)
    plot.add_tile(tile_provider)
    plot.patches(
        "xs",
        "ys",
        source=gds_polygons,
        fill_alpha=0.5,
        line_color="white",
        fill_color="teal",
    )
    return plot


def _plot_points(plot: Plot, points: pd.DataFrame) -> Figure:
    cds_lasso = ColumnDataSource(points)
    cds_lasso.selected.js_on_change(
        "indices",
        CustomJS(
            args=dict(source=cds_lasso),
            code="""
            document.dispatchEvent(
                new CustomEvent("LASSO_SELECT", {detail: {data: source.selected.indices}})
            )
            """,
        ),
    )
    plot.circle("x", "y", fill_alpha=1, size=5, source=cds_lasso)
    return plot


def _get_points_on_selection(bokeh_plot: Plot, points: gpd.GeoDataFrame) -> pd.Series:
    lasso_selected = streamlit_bokeh_events(
        bokeh_plot=bokeh_plot,
        events="LASSO_SELECT",
        key="bar",
        refresh_on_update=False,
        debounce_time=0,
    )
    if lasso_selected:
        try:
            indices_selected = lasso_selected.get("LASSO_SELECT")["data"]
        except:
            raise ValueError("No Small Areas selected!")
        small_areas_selected = points.iloc[indices_selected]["small_area"]
    else:
        small_areas_selected = points["small_area"]
    return small_areas_selected


def select_small_areas_on_map(boundaries, points) -> List[str]:
    basemap = _plot_basemap(boundaries)
    pointmap = _plot_points(plot=basemap, points=points)
    st.subheader("Select Dwellings by Small Area")
    st.markdown("> Click on the `Lasso Select` tool on the toolbar below!")
    small_areas_selected = _get_points_on_selection(bokeh_plot=pointmap, points=points)
    with st.beta_expander("Show Selected Small Areas"):
        st.write("Small Areas: " + str(small_areas_selected.to_list()))
    return small_areas_selected


if __name__ == "__main__":
    small_area_boundaries = load_small_area_boundaries()
    small_area_points = _convert_geometry_to_xy(small_area_boundaries)
    small_area_boundaries_geojson = _convert_to_geojson_str(small_area_boundaries)
    select_small_areas_on_map(small_area_boundaries_geojson, small_area_points)
