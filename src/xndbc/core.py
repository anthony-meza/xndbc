import xarray as xr
from typing import List, Union, Optional

from .ndbc import get_station_records, list_available as ndbc_list_available
from .station_metadata import get_stations


def list_available(
    mode: Optional[str] = "stdmet",
    lon_min: float = -180,
    lon_max: float = 180,
    lat_min: float = -90,
    lat_max: float = 90,
) -> xr.Dataset:
    """List stations or historical NDBC files as an xarray dataset."""
    stations = _filter_stations(get_stations(), lon_min, lon_max, lat_min, lat_max)
    if mode is None:
        return stations

    available = ndbc_list_available(mode=mode).to_dataframe()
    station_ids = {str(station_id) for station_id in stations.station_id.values}
    available = available.loc[available["station_id"].isin(station_ids)]
    available = available.reset_index(drop=True)
    available.index.name = "file"
    return available.to_xarray()


def _filter_stations(
    stations: xr.Dataset,
    lon_min: float,
    lon_max: float,
    lat_min: float,
    lat_max: float,
) -> xr.Dataset:
    return stations.where(
        (stations.longitude >= lon_min)
        & (stations.longitude <= lon_max)
        & (stations.latitude >= lat_min)
        & (stations.latitude <= lat_max),
        drop=True,
    )


def fetch_data(
    station_ids: Union[str, List[str]],
    years: Optional[Union[int, List[int]]] = None,
    sample_rate: str = "D",
    data_type: str = "historical",
    mode: Union[str, List[str]] = "stdmet",
    max_workers: int = 6,
) -> xr.Dataset:
    """Fetch historical or realtime buoy data for stations.

    This is the main function for retrieving buoy observational data. It handles
    data download and adds station location coordinates when available.

    Parameters
    ----------
    station_ids : str or list of str
        Station ID(s) to fetch data for. Can be a single station ID or a list.
    years : int or list of int, optional
        Year(s) to fetch data for. Can be a single year or a list/range.
        Required for historical data and ignored for realtime data.
    sample_rate : str, optional
        Temporal resampling rate (default: "D" for daily).
        Options: "D" (daily), "W" (weekly), "M" (monthly), "H" (hourly).
    data_type : {"historical", "realtime"}, optional
        Which NDBC feed to retrieve. Historical data is the default.
    mode : str or list of str, optional
        Which NDBC data mode(s) to retrieve (default is "stdmet").
    max_workers : int, optional
        Maximum number of concurrent file reads per station.

    Returns
    -------
    xr.Dataset
        Dataset containing buoy observations with time and station_id dimensions.

    Examples
    --------
    Fetch data for a single station and year:
    >>> data = xndbc.fetch_data("tplm2", 2020)

    Fetch multiple years of data:
    >>> data = xndbc.fetch_data("tplm2", range(2015, 2021))

    Fetch data from multiple stations:
    >>> data = xndbc.fetch_data(["tplm2", "44013"], range(2018, 2021))

    Fetch with weekly averaging:
    >>> data = xndbc.fetch_data("tplm2", 2020, sample_rate="W")

    Fetch realtime data:
    >>> data = xndbc.fetch_data("tplm2", data_type="realtime", sample_rate="H")

    Inspect returned variables:
    >>> data = xndbc.fetch_data("tplm2", range(2015, 2021))
    >>> list(data.data_vars)
    """
    if isinstance(station_ids, str):
        station_ids = [station_ids]
    else:
        station_ids = list(getattr(station_ids, "values", station_ids))
    station_ids = [str(station_id).lower() for station_id in station_ids]
    data_type = data_type.lower()
    mode = mode.lower() if isinstance(mode, str) else [m.lower() for m in mode]
    if years is not None:
        if isinstance(years, int):
            years = [years]
        elif isinstance(years, range):
            years = list(years)

    dataset = get_station_records(
        station_list=station_ids,
        years=years,
        sample_rate=sample_rate,
        data_type=data_type,
        mode=mode,
        max_workers=max_workers,
    )

    if "station_id" in dataset.coords and dataset.sizes.get("station_id", 0) > 0:
        station_locations = get_stations().reindex(station_id=dataset.station_id)
        dataset = dataset.assign_coords(
            latitude=("station_id", station_locations.latitude.data),
            longitude=("station_id", station_locations.longitude.data),
        )

    return dataset
