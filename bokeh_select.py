from typing import List
from bokeh.models.plots import Plot

from bokeh.plotting import figure
from bokeh.plotting import Figure
from bokeh.models import ColumnDataSource, CustomJS

import geopandas as gpd
import pandas as pd
import streamlit as st
from streamlit_bokeh_events import streamlit_bokeh_events


def _convert_geometry_to_xy(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return gdf.assign(
        x=lambda gdf: gdf.geometry.centroid.x, y=lambda gdf: gdf.geometry.centroid.y
    ).drop(columns="geometry")


def _plot_small_area_points(small_area_points) -> Figure:
    cds_lasso = ColumnDataSource(small_area_points)
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
    plot = figure(
        tools="pan, zoom_in, zoom_out, box_zoom, wheel_zoom, lasso_select",
        width=500,
        height=500,
    )
    plot.circle("x", "y", fill_alpha=0.5, size=5, source=cds_lasso)
    return plot


def _ask_user_for_small_areas(
    bokeh_plot: Plot, small_area_points: gpd.GeoDataFrame
) -> pd.Series:
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
        small_areas_selected = small_area_points.iloc[indices_selected]["small_area"]
    else:
        small_areas_selected = small_area_points["small_area"]
    return small_areas_selected


def select_small_areas(small_area_boundaries: gpd.GeoDataFrame) -> List[str]:
    small_area_points = _convert_geometry_to_xy(
        small_area_boundaries.set_crs(epsg="2157").to_crs(epsg="3857")
    )  # CARTODBPOSITRON requires this crs
    bokeh_plot = _plot_small_area_points(small_area_points)
    st.subheader("Select Dwellings by Small Area")
    st.markdown("> Click on the `Lasso Select` tool on the toolbar below!")
    small_areas_selected = _ask_user_for_small_areas(
        bokeh_plot=bokeh_plot, small_area_points=small_area_points
    )
    with st.beta_expander("Show Selected Small Areas"):
        st.write("Small Areas: " + str(small_areas_selected.to_list()))
    return small_areas_selected


if __name__ == "__main__":
    small_area_boundaries = gpd.read_file(
        "data/dublin_small_area_boundaries_2016",
    )
    select_small_areas(small_area_boundaries)
