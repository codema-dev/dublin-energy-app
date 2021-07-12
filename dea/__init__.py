from configparser import ConfigParser
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_SRC_DIR = Path(__file__).parent
_DATA_DIR = Path(__file__).parent.parent / "data"

CONFIG = ConfigParser()
CONFIG.read(_SRC_DIR / "config.ini")

with open(_SRC_DIR / "defaults.json") as f:
    DEFAULTS = json.load(f)
