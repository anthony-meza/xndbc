import pandas as pd
import xarray as xr

NDBC_STATION_TABLE_URL = "https://www.ndbc.noaa.gov/data/stations/station_table.txt"


def get_station_metadata() -> xr.Dataset:
    """Fetch the raw NDBC station metadata table as an ``xarray.Dataset``."""
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
    """Return simplified station notes with latitude/longitude coordinates."""
    metadata = get_station_metadata().to_dataframe()
    location = metadata["LOCATION"].str.split(expand=True)

    stations = pd.DataFrame(index=metadata.index.astype(str))
    stations["notes"] = metadata["NOTE"]
    stations["latitude"] = location[0].astype(float) * location[1].map({"N": 1, "S": -1})
    stations["longitude"] = location[2].astype(float) * location[3].map({"E": 1, "W": -1})

    return stations.to_xarray().set_coords(["latitude", "longitude"])
