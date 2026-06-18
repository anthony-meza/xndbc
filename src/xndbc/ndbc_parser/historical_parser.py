"""Historical NDBC file discovery and retrieval."""

from functools import lru_cache
import re
from typing import Optional

import pandas as pd
import xarray as xr

from .ndbc_parser import _read_noaa_text, _read_observation_table, _table_to_dataset

HISTORICAL_ROOT = "https://www.ndbc.noaa.gov/data/historical"


@lru_cache(maxsize=1)
def _list_historical_modes() -> list[str]:
    """List historical data modes advertised by NDBC."""
    return sorted(
        mode
        for mode in re.findall(r'href="([^"/]+)/"', _read_noaa_text(f"{HISTORICAL_ROOT}/"))
        if mode != ".."
    )


def _parse_historical_file(filename: str, mode: str) -> Optional[dict]:
    """Parse station and year from an NDBC historical filename."""
    match = re.fullmatch(r"(.+)[a-z](\d{4})\.txt\.gz", filename)
    if match is None:
        return None
    station_id, year = match.groups()
    return {"station_id": station_id.lower(), "mode": mode, "year": int(year), "filename": filename}


@lru_cache(maxsize=None)
def _build_mode_file_index(mode: str) -> pd.DataFrame:
    """Index historical files available for one NDBC data mode."""
    mode = mode.lower()
    root = f"{HISTORICAL_ROOT}/{mode}/"
    rows = [
        {**parsed, "url": f"{root}{filename}"}
        for filename in re.findall(r'href="([^"]+\.txt\.gz)"', _read_noaa_text(root))
        if (parsed := _parse_historical_file(filename, mode)) is not None
    ]
    return pd.DataFrame(rows, columns=["station_id", "mode", "year", "filename", "url"])


def _build_historical_file_index(modes: Optional[list[str]] = None) -> pd.DataFrame:
    """Index historical files across one or more NDBC data modes."""
    modes = _list_historical_modes() if modes is None else modes
    modes = [modes] if isinstance(modes, str) else modes
    frames = [_build_mode_file_index(mode) for mode in modes]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _list_historical_files(mode: Optional[str] = "stdmet") -> xr.Dataset:
    """List available historical files as an ``xarray.Dataset``."""
    modes = None if mode is None else [mode.lower()]
    available = _build_historical_file_index(modes).reset_index(drop=True)
    available.index.name = "file"
    return available.to_xarray()


def _historical_file_url(station_id: str, year: int, mode: str = "stdmet") -> str:
    """Return the historical data URL for a station, year, and mode."""
    available = _build_historical_file_index([mode.lower()])
    station_id = station_id.lower()
    matches = available.query("station_id == @station_id and year == @year")
    if matches.empty:
        raise ValueError(f"No historical {mode} file found for station {station_id}, year {year}")
    return matches.iloc[0]["url"]


def _fetch_historical_year(
    yr: int,
    station_id: str = "tplm2",
    sample_rate: str = "D",
    display_error: bool = False,
    mode: str = "stdmet",
) -> Optional[xr.Dataset]:
    """Fetch historical data for one station/year/mode."""
    try:
        return _table_to_dataset(_read_observation_table(_historical_file_url(station_id, yr, mode), mode=mode), mode, sample_rate)
    except Exception as error:
        if display_error:
            print(f"Error extracting data for station {station_id}, year {yr}: {error}")
        return None
