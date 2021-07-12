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


def improve_housing_quality(
    indiv_hh: pd.DataFrame,
    improvement: float,
    uvalue_columns: List[str],
    target_uvalues: Dict[str, float],
) -> pd.DataFrame:
    indiv_hh_improved = indiv_hh.copy()

    if not indiv_hh_improved.empty:
        portion_to_reduce_values_by = 1 - improvement

        current_uvalues_array = indiv_hh[uvalue_columns].to_numpy()
        target_uvalues_array = pd.DataFrame(target_uvalues).to_numpy()
        gap_to_target = current_uvalues_array - target_uvalues_array
        improved_uvalues_array = gap_to_target * portion_to_reduce_values_by

        improved_uvalues_all_positive = pd.DataFrame(
            np.where(improved_uvalues_array < 0, 0, improved_uvalues_array),
            columns=uvalue_columns,
        )
        small_areas = pd.Series(indiv_hh.index).rename("SMALL_AREA")
        improved_u_values_indexed = pd.concat(
            [small_areas, improved_uvalues_all_positive],
            axis=1,
        ).set_index("SMALL_AREA")

        indiv_hh_improved = indiv_hh_improved.drop(columns=uvalue_columns)
        indiv_hh_improved.loc[:, uvalue_columns] = improved_u_values_indexed

    return indiv_hh_improved
