import json
from typing import List

from bokeh.models.plots import Plot
from bokeh.plotting import figure
#from bokeh.plotting import Figure
from bokeh.models import ColumnDataSource
from bokeh.models import CustomJS
from bokeh.models import GeoJSONDataSource
from bokeh.tile_providers import CARTODBPOSITRON
from bokeh.tile_providers import get_provider
import geopandas as gpd
import pandas as pd
import streamlit as st
from streamlit_bokeh_events import streamlit_bokeh_events


@st.cache
def _convert_gdf_geometry_to_xy(gdf: gpd.GeoDataFrame, epsg: str) -> gpd.GeoDataFrame:
    return (
        gdf.to_crs(epsg=epsg)
        .assign(
            x=lambda gdf: gdf.geometry.centroid.x, y=lambda gdf: gdf.geometry.centroid.y
        )
        .drop(columns="geometry")
    )


@st.cache
def _convert_gdf_to_geojson_str(
    gdf: gpd.GeoDataFrame, epsg: str, tolerance_m: int = 50
) -> str:
    boundaries = gdf.to_crs(epsg=epsg).geometry.simplify(tolerance_m)
    return json.dumps(json.loads(boundaries.to_json()))


def _plot_basemap(boundaries: gpd.GeoDataFrame, epsg: str):
    geojson_str = _convert_gdf_to_geojson_str(boundaries, epsg=epsg)
    gds_polygons = GeoJSONDataSource(geojson=geojson_str)
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


def _plot_points(plot: Plot, points: pd.DataFrame) -> figure:
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
    plot.circle("x", "y", fill_alpha=1, size=1.5, source=cds_lasso)
    return plot


def _get_points_on_selection(
    column_name: str, bokeh_plot: Plot, points: gpd.GeoDataFrame
) -> List[str]:
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
            raise ValueError(f"No '{column_name}' selected!")
        points_selected = points.iloc[indices_selected][column_name]
    else:
        points_selected = points[column_name]
    return points_selected.to_list()


def mapselect(
    column_name: str, boundaries: gpd.GeoDataFrame, epsg: str = "3857"
) -> List[str]:
    """Select Polygons on a map corresponding to column_name.

    Args:
        column_name (str): Column in boundaries to be filtered by map selection
        boundaries (gpd.GeoDataFrame): Boundaries to be mapped
        epsg (str, optional):  EPSG registry. CARTODBPOSITRON tile requires epsg=3857.
            Defaults to "3857".

    Returns:
        List[str]: Polygons selected
    """
    st.subheader(f"Filter by {column_name}")
    st.markdown("> Click on the `Lasso Select` tool on the toolbar below!")
    points = _convert_gdf_geometry_to_xy(boundaries, epsg=epsg)
    basemap = _plot_basemap(boundaries, epsg=epsg)
    pointmap = _plot_points(plot=basemap, points=points)
    points_selected = _get_points_on_selection(
        column_name=column_name, bokeh_plot=pointmap, points=points
    )
    with st.expander(f"Show selected {column_name}"):
        st.write(str(points_selected))
    return points_selected
