from pathlib import Path
from typing import List
from typing import Tuple

import geopandas as gpd
from geopandas import GeoDataFrame
import numpy as np
import pandas as pd
from pandas import DataFrame
import plotly.express as px
import streamlit as st

data_dir = Path("./data")

st.title("Dublin Housing Energy Demand App")


@st.cache
def load_data(data_dir: Path) -> Tuple[DataFrame, DataFrame, GeoDataFrame]:

    indiv_hh_raw: DataFrame = pd.read_csv(data_dir / "streamlit_dublin_indiv_hh.csv")
    esri_forecast: DataFrame = pd.read_csv(
        data_dir / "esri_housing_forecast_12_2020.csv"
    )
    small_area_boundaries: GeoDataFrame = gpd.read_file(
        data_dir / "dublin_small_area_boundaries_2011.geojson", driver="GeoJSON"
    )

    return indiv_hh_raw, esri_forecast, small_area_boundaries


data_load_state = st.text("Loading data...")
data_dir = Path("data")
indiv_hh_raw, esri_forecast, small_area_boundaries = load_data(data_dir)
data_load_state.text("Loading data ... Done!")

if st.checkbox("Show ESRI Projections"):
    st.subheader("Structural Housing Demand Projections By Local Authority 2017-2014")
    st.markdown(
        "*Source: Bergin, A. and García-Rodríguez, A., 2020."
        " Regional demographics and structural housing demand at a county Level."
        " ESRI, Economic & Social Research Institute.*"
    )
    st.write(esri_forecast)

if st.checkbox("Show Individual Housing Sample"):
    st.write(indiv_hh_raw.sample(50))


scenario = st.selectbox(
    "Select a Scenario", ["50:50", "High Migration", "Low Migration"]
)

percentage_demand_met = st.slider("% Demand Met", min_value=0, max_value=100, value=50)
percentage_demand_met = percentage_demand_met / 100

year = st.slider("Year", min_value=2021, max_value=2040)


@st.cache
def project_la_housing_demand(
    esri_forecast: DataFrame, scenario: str = "50:50"
) -> DataFrame:

    scenarios_keys = {"High": "2040_high", "Low": "2040_low", "50:50": "2040_50_50"}
    return (
        esri_forecast.set_index("COUNTYNAME")
        .T.drop(["2017", "2026", "2031", "2040"])
        .loc[["2021", scenarios_keys[scenario]]]
        .rename({scenarios_keys[scenario]: "2040"})
        .reset_index()
        .assign(index=lambda df: df["index"].astype(int))
        .set_index("index")
        .reindex(range(2017, 2041, 1))
        .interpolate()
        .round()
        .loc[2021:]
    )


projected_la_housing_demand = project_la_housing_demand(esri_forecast)


@st.cache
def add_new_housing(
    indiv_hh: DataFrame,
    percentage_demand_met: float,
    projected_la_housing_demand: DataFrame,
    year: int,
    random_state: int = 42,
) -> DataFrame:

    annual_demand = projected_la_housing_demand.loc[year]
    all_new_housing: List[DataFrame] = []
    for la, demand in annual_demand.items():
        new_housing = (
            indiv_hh.query("local_authority == @la")
            .sample(int(demand), random_state=random_state)
            .loc[:, ["local_authority", "SMALL_AREA", "EDNAME"]]
            .assign(period_built="2021 or later")
        )
        all_new_housing.append(new_housing)


def calculate_small_area_demands(hh_small_areas, hh_demands):
    kwh_to_mwh_conversion_factor = 10 ** -3
    return (
        pd.concat([hh_small_areas, hh_demands], axis="columns")
        .groupby("SMALL_AREA")
        .sum()
        .multiply(kwh_to_mwh_conversion_factor)
        .round()
        .rename(columns={0: "demand_mwh_per_year"})
        .reset_index()
    )


def create_small_area_map(small_area_values, small_area_boundaries):
    return (
        small_area_values.merge(small_area_boundaries)
        .pipe(gpd.GeoDataFrame)
        .to_crs(epsg=4326)
    )


def extract_category(
    category: str,
    indiv_hh: pd.DataFrame,
    query: str,
) -> pd.DataFrame:
    if category:
        indiv_hh_extract = indiv_hh_raw.query(query)
    else:
        indiv_hh_extract = indiv_hh
    return indiv_hh_extract


local_authorities = [None] + list(indiv_hh_raw["local_authority"].unique())
local_authority = st.sidebar.selectbox("Select Local Authority", local_authorities)
indiv_hh_in_la = extract_category(
    local_authority, indiv_hh_raw, "local_authority == @local_authority"
)

electoral_districts = [None] + list(indiv_hh_raw["EDNAME"].unique())
electoral_district = st.sidebar.selectbox(
    "Select Electoral District", electoral_districts
)
indiv_hh_in_ed = extract_category(
    electoral_district, indiv_hh_raw, "EDNAME == @electoral_district"
)

indiv_hh_extract = indiv_hh_in_ed if electoral_district else indiv_hh_in_la

indiv_hh = indiv_hh_extract
hh_demands = indiv_hh["inferred_floor_area"] * indiv_hh["energy_kwh_per_m2_year"]
small_area_demands = calculate_small_area_demands(indiv_hh["SMALL_AREA"], hh_demands)
total_demand = hh_demands.sum()
small_area_demand_map = create_small_area_map(small_area_demands, small_area_boundaries)


@st.cache
def plot_plotly_map(small_area_demand_map):
    init_x = small_area_demand_map.geometry.centroid.x.mean()
    init_y = small_area_demand_map.geometry.centroid.y.mean()
    return px.choropleth_mapbox(
        small_area_demand_map,
        geojson=small_area_demand_map.geometry,
        locations=small_area_demand_map.index,
        hover_data=["SMALL_AREA", "demand_mwh_per_year"],
        labels={
            "SMALL_AREA": "Small Area ID",
            "demand_mwh_per_year": "Demand [MWh/year]",
        },
        color="demand_mwh_per_year",
        center={"lat": init_y, "lon": init_x},
        mapbox_style="open-street-map",
        height=900,
        width=800,
        opacity=0.75,
        zoom=9,
    )


map_load_state = st.text("Creating map...")
fig = plot_plotly_map(small_area_demand_map)
st.plotly_chart(fig)
map_load_state.text("Creating map... Done!")
