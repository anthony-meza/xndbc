"""NDBC parsing and retrieval helpers."""

from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from tqdm.auto import tqdm
import xarray as xr

from .historical_parser import _fetch_historical_year, _list_historical_files
from .realtime_parser import _fetch_realtime_station

__all__ = ["fetch_station_records", "_list_historical_files"]


def fetch_station_records(
    station_list: list[str],
    years: Optional[list[int]] = None,
    sample_rate: str = "D",
    data_type: str = "historical",
    mode: str = "stdmet",
    max_workers: int = 6,
) -> xr.Dataset:
    """Retrieve and combine NDBC records for stations, years, and modes."""
    station_datasets = []
    for station_id in tqdm(station_list, desc="Fetching stations", unit="station"):
        if data_type == "realtime":
            datasets = [_fetch_realtime_station(station_id, sample_rate, mode=mode)]
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                datasets = list(executor.map(lambda yr: _fetch_historical_year(yr, station_id, sample_rate, mode=mode), years))

        datasets = [ds for ds in datasets if ds is not None]
        if datasets:
            dataset = xr.concat(datasets, dim="time").sortby("time").drop_duplicates("time")
            station_datasets.append(dataset.assign_coords(station_id=station_id).expand_dims("station_id"))

    return xr.merge(station_datasets, compat="no_conflicts", join="outer") if station_datasets else xr.Dataset()
