"""Realtime NDBC URL construction and retrieval."""

from typing import Optional

import xarray as xr

from .ndbc_parser import _read_observation_table, _table_to_dataset

REALTIME_ROOT = "https://www.ndbc.noaa.gov/data/realtime2"
REALTIME_EXTENSIONS = {
    "stdmet": "txt",
    "adcp": "adcp",
    "cwind": "cwind",
    "ocean": "ocean",
    "spec": "spec",
    "supl": "supl",
    "swden": "swden",
    "swdir": "swdir",
    "swdir2": "swdir2",
    "swr1": "swr1",
    "swr2": "swr2",
}


def _realtime_file_url(station_id: str, mode: str = "stdmet") -> str:
    """Return the realtime data URL for a station and mode."""
    mode = mode.lower()
    if mode not in REALTIME_EXTENSIONS:
        raise ValueError(f"Unsupported realtime mode: {mode}")
    return f"{REALTIME_ROOT}/{station_id.upper()}.{REALTIME_EXTENSIONS[mode]}"


def _fetch_realtime_station(
    station_id: str = "tplm2",
    sample_rate: str = "H",
    display_error: bool = False,
    mode: str = "stdmet",
) -> Optional[xr.Dataset]:
    """Fetch realtime data for one station/mode."""
    try:
        return _table_to_dataset(_read_observation_table(_realtime_file_url(station_id, mode), mode=mode), mode, sample_rate)
    except Exception as error:
        if display_error:
            print(f"Error extracting realtime data for station {station_id}: {error}")
        return None
