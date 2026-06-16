import pandas as pd
import xarray as xr

NDBC_STATION_TABLE_URL = "https://www.ndbc.noaa.gov/data/stations/station_table.txt"


def get_station_metadata() -> xr.Dataset:
    """Fetch raw NDBC station metadata."""
    stations = pd.read_csv(
        NDBC_STATION_TABLE_URL,
        sep="|",
        na_values="",
    ).iloc[1:].fillna(" ")

    stations.rename(columns={stations.columns[0]: "station_id"}, inplace=True)
    stations = stations.rename(columns=lambda x: x.strip())
    stations["station_id"] = stations["station_id"].astype(str).str.strip().str.lower()
    return stations.set_index("station_id").to_xarray()


def get_stations() -> xr.Dataset:
    """Get station notes and location coordinates."""
    metadata = get_station_metadata().to_dataframe()
    lat = lambda location: float(location.split()[0]) * (1 if location.split()[1] == "N" else -1)
    lon = lambda location: float(location.split()[2]) * (1 if location.split()[3] == "E" else -1)

    stations = pd.DataFrame(index=metadata.index.astype(str))
    stations["notes"] = metadata["NOTE"]
    stations["latitude"] = metadata["LOCATION"].apply(lat)
    stations["longitude"] = metadata["LOCATION"].apply(lon)

    return stations.to_xarray().set_coords(["latitude", "longitude"])
