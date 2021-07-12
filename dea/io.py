from pathlib import Path
from typing import Callable

import fsspec


def load(read: Callable, url: str, data_dir: Path, filesystem_name: str):
    filename = url.split("/")[-1]
    filepath = data_dir / filename
    if not filepath.exists():
        fs = fsspec.filesystem(filesystem_name)
        with fs.open(url, cache_storage=filepath) as f:
            df = read(f)
    else:
        df = read(filepath)
    return df
