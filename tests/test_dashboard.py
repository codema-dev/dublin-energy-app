import pandas as pd
from pandas.testing import assert_frame_equal

from dublin_energy_app.dashboard import improve_housing_quality


def test_improve_housing_quality():
    individual_building = pd.DataFrame(
        {
            "Door Weighted Uvalue": {"268001002": 3.0},
            "Floor Weighted Uvalue": {"268001002": 0.6},
            "Roof Weighted Uvalue": {"268001002": 0.4},
            "Wall weighted Uvalue": {"268001002": 0.6},
            "WindowsWeighted Uvalue": {"268001002": 2.8},
        }
    )
    improvement = 0.5
    expected_output = pd.DataFrame(
        {
            "Door Weighted Uvalue": {"268001002": 1.45},
            "Floor Weighted Uvalue": {"268001002": 0.275},
            "Roof Weighted Uvalue": {"268001002": 0.195},
            "Wall weighted Uvalue": {"268001002": 0.25},
            "WindowsWeighted Uvalue": {"268001002": 1.2},
        }
    )

    output = improve_housing_quality(
        indiv_hh=individual_building,
        improvement=improvement,
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

    assert_frame_equal(output, expected_output)