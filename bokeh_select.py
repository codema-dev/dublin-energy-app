from typing import List

from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, CustomJS
from bokeh.models import DataTable, TableColumn
from bokeh.io import output_notebook

import geopandas as gpd
import streamlit as st
from streamlit_bokeh_events import streamlit_bokeh_events

output_notebook()


def select_small_areas(small_area_boundaries: gpd.GeoDataFrame) -> List[str]:
    small_area_boundaries["x"] = small_area_boundaries.geometry.centroid.x
    small_area_boundaries["y"] = small_area_boundaries.geometry.centroid.y
    small_area_boundaries = small_area_boundaries.drop(columns="geometry")

    cds_lasso = ColumnDataSource(small_area_boundaries)
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
        width=250,
        height=250,
    )

    plot.circle("x", "y", fill_alpha=0.5, size=5, source=cds_lasso)
    result_lasso = streamlit_bokeh_events(
        bokeh_plot=plot,
        events="LASSO_SELECT",
        key="bar",
        refresh_on_update=False,
        debounce_time=0,
    )
    if result_lasso:
        if result_lasso.get("LASSO_SELECT"):
            df_extract = small_area_boundaries.iloc[
                result_lasso.get("LASSO_SELECT")["data"]
            ]
            st.write(df_extract.sum())


if __name__ == "__main__":
    small_area_boundaries = gpd.read_file(
        "data/dublin_small_area_boundaries_2016",
    )
    select_small_areas(small_area_boundaries)
