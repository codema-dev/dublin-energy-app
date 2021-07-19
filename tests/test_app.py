from pathlib import Path
import sys

import pandas as pd
import pytest

parentdir = Path(__name__).parent.parent
sys.path.insert(0, str(parentdir))

import app


def test_filter_buildings_raises_error_when_no_buildings():
    selections = {
        "small_area": [1],
        "energy_rating": ["G"],
    }
    with pytest.raises(ValueError):
        app._filter_buildings(
            buildings=pd.DataFrame({"small_area": [1], "energy_rating": ["A"]}),
            selections=selections,
        )
