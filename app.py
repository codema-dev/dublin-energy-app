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

percentage_demand_met = st.slider(
    "Percentage of Projected Housing Demand Built",
    min_value=0,
    max_value=100,
    value=50,
)
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
        .cumsum()
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


indiv_hh_latest = add_new_housing(
    indiv_hh_raw,
    percentage_demand_met=percentage_demand_met,
    projected_la_housing_demand=projected_la_housing_demand,
    year=year,
    random_state=42,
)

local_authorities = [None] + list(indiv_hh_latest["local_authority"].unique())
local_authority = st.sidebar.selectbox("Select Local Authority", local_authorities)
indiv_hh_in_la = extract_category(
    local_authority, indiv_hh_latest, "local_authority == @local_authority"
)

electoral_districts = [None] + list(indiv_hh_latest["EDNAME"].unique())
electoral_district = st.sidebar.selectbox(
    "Select Electoral District", electoral_districts
)
indiv_hh_in_ed = extract_category(
    electoral_district, indiv_hh_latest, "EDNAME == @electoral_district"
)

indiv_hh_extract = indiv_hh_in_ed if electoral_district else indiv_hh_in_la

indiv_hh = indiv_hh_extract
hh_demands = indiv_hh["inferred_floor_area"] * indiv_hh["energy_kwh_per_m2_year"]
small_area_demands = calculate_small_area_demands(indiv_hh["SMALL_AREA"], hh_demands)
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


total_demand = hh_demands.sum() / 10 ** 6
st.write("Total Demand [GWh/year]:")
st.write(total_demand)

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
