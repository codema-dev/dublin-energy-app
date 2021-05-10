import json
from pathlib import Path
from typing import Dict
from typing import List
from typing import Tuple

import geopandas as gpd
from geopandas import GeoDataFrame
import numpy as np
import pandas as pd
from pandas import DataFrame
import plotly.express as px
import streamlit as st

from dublin_energy_app.deap import calculate_heat_loss_parameter
from dublin_energy_app import dashboard

KWH_TO_MWH = 10 ** -3


@st.cache
def load_data(data_dir: Path) -> Tuple[DataFrame, DataFrame, GeoDataFrame]:

    indiv_hh_raw = pd.read_parquet(data_dir / "dublin_indiv_hh.parquet").set_index(
        "SMALL_AREA"
    )
    with open(data_dir / "archetype_new_build.json", "r") as file:
        archetype_new_build = pd.Series(json.load(file))
    esri_forecast = pd.read_csv(data_dir / "esri_housing_forecast_12_2020.csv")
    small_area_boundaries = (
        gpd.read_file(
            data_dir / "dublin_small_area_boundaries_2011.geojson", driver="GeoJSON"
        )
        .to_crs(epsg=4326)
        .set_index("SMALL_AREA")
    )

    return indiv_hh_raw, archetype_new_build, esri_forecast, small_area_boundaries


def show_housing_projections(esri_forecast):
    if st.checkbox("Show Housing Demand Projections"):
        st.subheader(
            "Structural Housing Demand Projections By Local Authority 2017-2014"
        )
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


def show_housing_sample(indiv_hh_raw):
    if st.checkbox("Show Individual Housing Sample"):
        st.markdown(
            "This is a sample of the individual households used in the demand calculation"
        )
        st.write(indiv_hh_raw.sample(50))


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


def select_zone(indiv_hh: pd.DataFrame):
    local_authority = st.sidebar.selectbox("Select Local Authority", LOCAL_AUTHORITIES)
    electoral_district = st.sidebar.selectbox(
        "Select Electoral District", ELECTORAL_DISTRICTS
    )

    if (electoral_district is not None) & (local_authority is not None):
        raise ValueError(
            "Cannot select both local_authority and electoral_district,"
            " please unselect one of them!"
        )
    if electoral_district:
        zone = electoral_district
        zone_type = "electoral_district"
    elif local_authority:
        zone = local_authority
        zone_type = "local_authority"
    else:
        zone = None
        zone_type = None

    return zone, zone_type


@st.cache
def extract_zone(
    indiv_hh: pd.DataFrame,
    zone: str,
    zone_type: str,
) -> pd.DataFrame:

    if zone_type == "local_authority":
        query = "local_authority == @zone"
    elif zone_type == "electoral_district":
        query = "EDNAME == @zone"

    if zone:
        indiv_hh_extract = indiv_hh_raw.query(query)
    else:
        indiv_hh_extract = indiv_hh

    return indiv_hh_extract


@st.cache
def simulate_new_housing(
    indiv_hh: DataFrame,
    archetype_new_build: pd.Series,
    percentage_demand_met: float,
    projected_la_housing_demand: DataFrame,
    year: int,
    random_state: int = 42,
) -> DataFrame:

    if percentage_demand_met == 0:
        new_housing = pd.DataFrame()
    else:
        annual_demand = projected_la_housing_demand.loc[year]
        new_housing_by_la: List[DataFrame] = []
        for la, demand in annual_demand.items():
            la_total_new_buildings = int(demand * percentage_demand_met)
            la_new_housing = (
                indiv_hh.query("local_authority == @la")
                .sample(la_total_new_buildings, random_state=random_state)
                .loc[:, ["local_authority", "EDNAME"]]
            )
            new_housing_by_la.append(la_new_housing)

        new_housing_raw = pd.concat(new_housing_by_la).reset_index()
        archetype_properties = archetype_new_build.to_frame().T
        archetype_broadcast = pd.concat(
            [archetype_properties] * len(new_housing_raw)
        ).reset_index()  # broadcast archetype to the same length as new housing

        new_housing = pd.concat(
            [new_housing_raw, archetype_broadcast], axis=1
        ).set_index("SMALL_AREA")

    return new_housing


def select_building_subset() -> List[str]:
    st.subheader("Select Building Subset for a Retrofit Scenario")
    c1, c2, c3, c4, c5 = st.beta_columns(5)
    before_1919 = "before 1919" if c1.checkbox("before 1919") else None
    from_19_to_45 = "1919 - 1945" if c2.checkbox("1919 - 1945") else None
    from_46_to_60 = "1946 - 1960" if c3.checkbox("1946 - 1960") else None
    from_61_to_70 = "1961 - 1970" if c4.checkbox("1961 - 1970") else None
    from_71_to_80 = "1971 - 1980" if c5.checkbox("1971 - 1980") else None
    from_81_to_80 = "1981 - 1990" if c1.checkbox("1981 - 1990") else None
    from_91_to_00 = "1991 - 2000" if c2.checkbox("1990 - 2000") else None
    from_01_to_05 = "2001 - 2005" if c3.checkbox("2001 - 2005") else None
    from_06_to_10 = "2006 - 2010" if c4.checkbox("2006 - 2010") else None
    later_than_11 = "2011 or later" if c5.checkbox("2011 or later") else None
    options_selected = [
        before_1919,
        from_19_to_45,
        from_46_to_60,
        from_61_to_70,
        from_71_to_80,
        from_81_to_80,
        from_91_to_00,
        from_06_to_10,
        from_06_to_10,
        later_than_11,
    ]
    return [o for o in options_selected if o]


@st.cache
def calculate_heat_demand(
    indiv_hh: pd.DataFrame,
) -> pd.DataFrame:
    typical_boiler_efficiency = 0.85
    indiv_hh_heat_mwh_per_year = (
        indiv_hh["total_floor_area"]
        * indiv_hh["Energy Value"]
        * typical_boiler_efficiency
        * KWH_TO_MWH
    )
    return indiv_hh_heat_mwh_per_year.rename("heat_mwh_per_year")


@st.cache
def calculate_heat_pump_viability(indiv_hh: pd.DataFrame) -> pd.DataFrame:
    # 90% of GroundFloorHeight within (2.25, 2.75) in BER Public
    assumed_floor_height = 2.5
    thermal_bridging_factor = 0.15  # 87% of ThermalBridgingFactor in BER Public
    heat_loss_parameter_cutoff = 2.3  # SEAI, Tech Advisor Role Heat Pumps 2020
    heat_loss_parameter = calculate_heat_loss_parameter(
        roof_area=indiv_hh["Roof Total Area"],
        roof_uvalue=indiv_hh["Roof Weighted Uvalue"],
        wall_area=indiv_hh["Wall Total Area"],
        wall_uvalue=indiv_hh["Wall weighted Uvalue"],
        floor_area=indiv_hh["Floor Total Area"],
        floor_uvalue=indiv_hh["Floor Weighted Uvalue"],
        window_area=indiv_hh["Windows Total Area"],
        window_uvalue=indiv_hh["WindowsWeighted Uvalue"],
        door_area=indiv_hh["Door Total Area"],
        door_uvalue=indiv_hh["Door Weighted Uvalue"],
        total_floor_area=indiv_hh["total_floor_area"],
        thermal_bridging_factor=thermal_bridging_factor,
        effective_air_rate_change=indiv_hh["effective_air_rate_change"],
        no_of_storeys=indiv_hh["No Of Storeys"],
        assumed_floor_height=assumed_floor_height,
    )
    return (
        pd.cut(
            heat_loss_parameter,
            bins=[0, heat_loss_parameter_cutoff, np.inf],
            labels=[True, False],
        )
        .astype("bool")
        .rename("heat_pump_ready")
    )


def set_map_zoom(zone_type: str):
    if zone_type == "local_authority":
        zoom = 9.5
    elif zone_type == "electoral_district":
        zoom = 13
    else:
        zoom = 9
    return zoom


def select_map_layer() -> str:
    color_selected = st.selectbox(
        label="Select Map Layer",
        options=["% Heat Pump Ready", "Heat Demand"],
        index=0,
    )
    if color_selected == "Heat Demand":
        map_color = "heat_mwh_per_year"
    else:
        map_color = "percentage_heat_pump_ready"
    return map_color


def plot_plotly_choropleth_mapbox_map(
    small_areas: GeoDataFrame,
    zoom: float,
    labels: Dict[str, str],
    hover_data: List[str],
    color: str,
):
    init_x = small_areas.geometry.centroid.x.mean()
    init_y = small_areas.geometry.centroid.y.mean()
    return px.choropleth_mapbox(
        small_areas,
        geojson=small_areas.geometry,
        locations=small_areas.index,
        hover_data=hover_data,
        labels=labels,
        color=color,
        center={"lat": init_y, "lon": init_x},
        mapbox_style="open-street-map",
        height=900,
        width=800,
        opacity=0.75,
        zoom=zoom,
    )


data_dir = Path("./data")

st.title("Dublin Housing Energy Demand App")
indiv_hh_raw, archetype_new_build, esri_forecast, small_area_boundaries = load_data(
    data_dir
)
LOCAL_AUTHORITIES = [None] + list(indiv_hh_raw["local_authority"].unique())
ELECTORAL_DISTRICTS = [None] + list(indiv_hh_raw["EDNAME"].unique())

show_housing_projections(esri_forecast)
show_housing_sample(indiv_hh_raw)

zone, zone_type = select_zone(indiv_hh_raw)
indiv_hh_in_zone = extract_zone(indiv_hh_raw, zone, zone_type)

scenario = st.sidebar.selectbox(
    "Select a Housing Growth Scenario", ["50:50", "High Migration", "Low Migration"]
)
year = st.sidebar.slider("Year", min_value=2021, max_value=2040)
percentage_demand_met = (
    st.sidebar.slider(
        "% Projected Housing Demand Built",
        min_value=0,
        max_value=100,
        value=0,
    )
    / 100
)

projected_la_housing_demand = project_la_housing_demand(esri_forecast)

indiv_hh_new = simulate_new_housing(
    indiv_hh_raw,
    archetype_new_build,
    percentage_demand_met=percentage_demand_met,
    projected_la_housing_demand=projected_la_housing_demand,
    year=year,
    random_state=42,
)
indiv_hh_new_in_zone = pd.concat(
    [indiv_hh_in_zone, indiv_hh_new], join="inner"
)  # get new buildings that are in the selected zone
indiv_hh_at_year = pd.concat([indiv_hh_in_zone, indiv_hh_new_in_zone]).dropna(how="all")

periods_built_selected = select_building_subset()
improvement = (
    st.slider(r"% Fabric Improvement of Subset", min_value=0, max_value=100) / 100
)
indiv_hh_subset = indiv_hh_at_year.query("period_built == @periods_built_selected")
indiv_hh_remaining = indiv_hh_at_year.query("period_built != @periods_built_selected")
indiv_hh_improved = dashboard.improve_housing_quality(
    indiv_hh_subset,
    improvement,
    uvalue_columns=[
        "Door Weighted Uvalue",
        "Floor Weighted Uvalue",
        "Roof Weighted Uvalue",
        "Wall weighted Uvalue",
        "WindowsWeighted Uvalue",
    ],
    target_uvalues={
        "Door Weighted Uvalue": [0.1],
        "Floor Weighted Uvalue": [0.05],
        "Roof Weighted Uvalue": [0.01],
        "Wall weighted Uvalue": [0.1],
        "WindowsWeighted Uvalue": [0.4],
    },
)

indiv_hh = pd.concat([indiv_hh_improved, indiv_hh_remaining])

overall_ber_ratings = pd.cut(
    indiv_hh["Energy Value"],
    bins=[-np.inf, 75, 150, 225, 300, 360, 450, np.inf],
    labels=["A", "B", "C", "D", "E", "F", "G"],
).value_counts()

indiv_hh_heat_mwh_per_year = calculate_heat_demand(indiv_hh)
small_area_heat_mwh_per_year = indiv_hh_heat_mwh_per_year.groupby(level=0).sum().round()

indiv_hh_heat_pump_viability = calculate_heat_pump_viability(indiv_hh)
small_area_percentage_heat_pump_ready = (
    indiv_hh_heat_pump_viability.groupby(level=0)
    .apply(lambda x: 100 * round(x.sum() / len(x), 2))
    .rename("percentage_heat_pump_ready")
)

total_housing = len(indiv_hh)
total_new_housing = len(indiv_hh_new)
total_heat_pump_reading_housing = indiv_hh_heat_pump_viability.sum()
percentage_heat_pump_ready_housing = round(
    100 * total_heat_pump_reading_housing / total_housing, 2
)
total_heat_demand = round(indiv_hh_heat_mwh_per_year.sum(), 2)

t1, t2 = st.beta_columns(2)
t1.subheader("Stock Statistics")
t1.markdown(
    f"""
    <table>
        <tr>
            <th>Total Housing</th>
            <td rowspan=2>{total_housing}</td>
        <tr>
        <tr>
            <th>Heat Pump<br>Ready Housing</th>
            <td>{total_heat_pump_reading_housing}</td>
        <tr>
        <tr>
            <th>New Housing</th>
            <td>{total_new_housing}</td>
        <tr>
        <tr>
            <th>% Housing Ready<br>for Heat Pumps</th>
            <td>{percentage_heat_pump_ready_housing}%</td>
        <tr>
            <th>Heat Demand<br>[MWh/year]</th>
            <td>{total_heat_demand}</td>
        <tr>
    </table>
    <br>
    """,
    unsafe_allow_html=True,
)

t2.subheader("Overall BER Ratings")
t2.markdown(
    f"""
    <table>
        <tr>
            <th>A</th>
            <td>{overall_ber_ratings.loc["A"]}</td>
        <tr>
        <tr>
            <th>B</th>
            <td>{overall_ber_ratings.loc["B"]}</td>
        <tr>
        <tr>
            <th>C</th>
            <td>{overall_ber_ratings.loc["C"]}</td>
        <tr>
        <tr>
            <th>D</th>
            <td>{overall_ber_ratings.loc["D"]}</td>
        <tr>
        <tr>
            <th>E</th>
            <td>{overall_ber_ratings.loc["E"]}</td>
        <tr>
        <tr>
            <th>F</th>
            <td>{overall_ber_ratings.loc["F"]}</td>
        <tr>
        <tr>
            <th>G</th>
            <td>{overall_ber_ratings.loc["G"]}</td>
        <tr>
    </table>
    """,
    unsafe_allow_html=True,
)

st.subheader("Map")
map_pressed = st.button("Create Map of Building Stock?")
if map_pressed:
    small_area_map = small_area_boundaries.join(small_area_heat_mwh_per_year).join(
        small_area_percentage_heat_pump_ready
    )
    zoom = set_map_zoom(zone_type)
    map_layer = select_map_layer()
    fig = plot_plotly_choropleth_mapbox_map(
        small_area_map,
        zoom=zoom,
        labels={
            "EDNAME": "Electoral District",
            "heat_mwh_per_year": "Heat Demand [MWh/year]",
            "percentage_heat_pump_ready": "% Heat Pump Ready",
        },
        hover_data=[
            "EDNAME",
            "heat_mwh_per_year",
            "percentage_heat_pump_ready",
        ],
        color=map_layer,
    )
    st.plotly_chart(fig)
