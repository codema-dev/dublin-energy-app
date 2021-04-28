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


@st.cache
def add_new_housing(
    indiv_hh: DataFrame,
    percentage_demand_met: float,
    projected_la_housing_demand: DataFrame,
    year: int,
    random_state: int = 42,
) -> DataFrame:

    annual_demand = projected_la_housing_demand.loc[year]
    new_housing_by_la: List[DataFrame] = []
    for la, demand in annual_demand.items():
        la_total_new_buildings = int(demand * percentage_demand_met)
        la_new_housing = (
            indiv_hh.query("local_authority == @la")
            .sample(la_total_new_buildings, random_state=random_state)
            .loc[:, ["local_authority", "SMALL_AREA", "EDNAME"]]
            .assign(period_built="2021 or later")
        )
        new_housing_by_la.append(la_new_housing)

    new_housing = pd.concat(new_housing_by_la).assign(
        inferred_ber="A", energy_kwh_per_m2_year=25
    )

    return (
        pd.concat([indiv_hh, new_housing])
        .reset_index(drop=True)
        .assign(
            inferred_floor_area=lambda df: df.groupby("SMALL_AREA")[
                "inferred_floor_area"
            ].apply(lambda x: x.fillna(x.median()))
        )
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


@st.cache
def plot_plotly_map(small_area_demand_map):
    init_x = small_area_demand_map.geometry.centroid.x.mean()
    init_y = small_area_demand_map.geometry.centroid.y.mean()
    return px.choropleth_mapbox(
        small_area_demand_map,
        geojson=small_area_demand_map.geometry,
        locations=small_area_demand_map.index,
        hover_data=["SMALL_AREA", "EDNAME", "demand_mwh_per_year"],
        labels={
            "SMALL_AREA": "Small Area ID",
            "EDNAME": "Electoral District",
            "demand_mwh_per_year": "Demand [MWh/year]",
        },
        color="demand_mwh_per_year",
        center={"lat": init_y, "lon": init_x},
        mapbox_style="open-street-map",
        height=900,
        width=800,
        opacity=0.5,
        color_continuous_scale="bluered",
        zoom=9,
    )


data_dir = Path("./data")

st.title("Dublin Housing Energy Demand App")
indiv_hh_raw, esri_forecast, small_area_boundaries = load_data(data_dir)

if st.checkbox("Show Housing Demand Projections"):
    st.subheader("Structural Housing Demand Projections By Local Authority 2017-2014")
    st.markdown(
        "These housing demand projections are used to estimate the housing demand in"
        " Dublin at any given year."
    )
    st.markdown(
        "*__Source__: Bergin, A. and García-Rodríguez, A., 2020."
        " Regional demographics and structural housing demand at a county Level."
        " ESRI, Economic & Social Research Institute.*"
    )
    st.write(esri_forecast)

if st.checkbox("Show Individual Housing Sample"):
    st.markdown(
        "This is a sample of the individual households used in the demand calculation"
    )
    st.write(indiv_hh_raw.sample(50))

scenario = st.sidebar.selectbox(
    "Select a Scenario", ["50:50", "High Migration", "Low Migration"]
)

percentage_demand_met = (
    st.sidebar.slider(
        "Percentage of Projected Housing Demand Built",
        min_value=0,
        max_value=100,
        value=50,
    )
    / 100
)

year = st.slider("Year", min_value=2021, max_value=2040)

projected_la_housing_demand = project_la_housing_demand(esri_forecast)

indiv_hh_at_year = add_new_housing(
    indiv_hh_raw,
    percentage_demand_met=percentage_demand_met,
    projected_la_housing_demand=projected_la_housing_demand,
    year=year,
    random_state=42,
)

local_authorities = [None] + list(indiv_hh_at_year["local_authority"].unique())
local_authority = st.sidebar.selectbox("Select Local Authority", local_authorities)
indiv_hh_in_la = extract_category(
    local_authority, indiv_hh_at_year, "local_authority == @local_authority"
)

electoral_districts = [None] + list(indiv_hh_at_year["EDNAME"].unique())
electoral_district = st.sidebar.selectbox(
    "Select Electoral District", electoral_districts
)
indiv_hh_in_ed = extract_category(
    electoral_district, indiv_hh_at_year, "EDNAME == @electoral_district"
)

indiv_hh_extract = indiv_hh_in_ed if electoral_district else indiv_hh_in_la

indiv_hh = indiv_hh_extract
hh_demands = indiv_hh["inferred_floor_area"] * indiv_hh["energy_kwh_per_m2_year"]
small_area_demands = calculate_small_area_demands(indiv_hh["SMALL_AREA"], hh_demands)
small_area_demand_map = create_small_area_map(small_area_demands, small_area_boundaries)

kwh_to_gwh_conversion_factor = 10 ** -9
total_demand = round(hh_demands.sum() * kwh_to_gwh_conversion_factor, 2)

left_column, right_column = st.beta_columns(2)
left_column.write("Estimated Total Demand [GWh/year]")
right_column.write(total_demand)

fig = plot_plotly_map(small_area_demand_map)
st.plotly_chart(fig)
