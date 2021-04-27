import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.express as px
import seaborn as sns
import streamlit as st

st.title("Dublin Housing Energy Demand App")

data_load_state = st.text("Loading data...")
dtypes = {
    # "COUNTYNAME": "category",
    # "SMALL_AREA": "category",
    # "EDNAME": "category",
    # "period_built": "category",
    "inferred_floor_area": "int32",
    # "inferred_ber": "category",
    "energy_kwh_per_m2_year": "int32",
}
indiv_hh = pd.read_csv("data/streamlit_dublin_indiv_hh.csv", dtype=dtypes)
esri_forecast = pd.read_csv("data/esri_housing_forecast_12_2020.csv")
small_area_boundaries = gpd.read_file(
    "data/Dublin_Census2011_Small_Areas_generalised20m"
)
data_load_state.text("Loading data ... Done!")

st.subheader("Structural Housing Demand Projections By Local Authority 2017-2014")
st.markdown(
    "*Source: Bergin, A. and García-Rodríguez, A., 2020."
    " Regional demographics and structural housing demand at a county Level."
    " ESRI, Economic & Social Research Institute.*"
)
st.write(esri_forecast)
st.write(indiv_hh.head())

local_authority = st.sidebar.selectbox(
    "Select Local Authority", indiv_hh["COUNTYNAME"].unique()
)

indiv_hh_small_areas = indiv_hh["SMALL_AREA"]
floor_area = indiv_hh["inferred_floor_area"]
energy_kwh_per_m2_year = indiv_hh["energy_kwh_per_m2_year"]
demand = energy_kwh_per_m2_year * floor_area
total_demand = demand.sum()
kwh_to_mwh_conversion_factor = 10 ** -3
small_area_demand_map = (
    pd.concat([indiv_hh_small_areas, demand], axis="columns")
    .groupby("SMALL_AREA")
    .sum()
    .multiply(kwh_to_mwh_conversion_factor)
    .round()
    .rename(columns={0: "demand_mwh_per_year"})
    .reset_index()
    .merge(small_area_boundaries)
    .pipe(gpd.GeoDataFrame)
    .to_crs(epsg=4326)
)

map_load_state = st.text("Creating map...")
init_x = small_area_demand_map.geometry.centroid.x.mean()
init_y = small_area_demand_map.geometry.centroid.y.mean()
fig = px.choropleth_mapbox(
    small_area_demand_map,
    geojson=small_area_demand_map.geometry,
    locations=small_area_demand_map.index,
    hover_data=["SMALL_AREA", "demand_mwh_per_year"],
    labels={"SMALL_AREA": "Small Area ID", "demand_mwh_per_year": "Demand [MWh/year]"},
    color="demand_mwh_per_year",
    center={"lat": init_y, "lon": init_x},
    mapbox_style="open-street-map",
    height=900,
    width=800,
    opacity=0.75,
    zoom=9,
)
st.plotly_chart(fig)
map_load_state.text("Creating map... Done!")
