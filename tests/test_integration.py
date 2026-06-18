"""Live NOAA integration tests for xndbc."""

import pytest
import xarray as xr

import xndbc
from xndbc import station_metadata

pytestmark = pytest.mark.integration


def test_public_api_is_available():
    assert isinstance(xndbc.__version__, str)
    assert callable(xndbc.list_available)
    assert callable(xndbc.fetch_data)


def test_list_available_mode_none_returns_live_stations():
    stations = xndbc.list_available(mode=None)

    assert isinstance(stations, xr.Dataset)
    assert "latitude" in stations.coords
    assert "longitude" in stations.coords
    assert stations.sizes["station_id"] > 0


def test_list_available_filters_live_stations_by_bounds():
    filtered = xndbc.list_available(mode=None, lon_min=-80, lon_max=-65, lat_min=25, lat_max=45)

    assert isinstance(filtered, xr.Dataset)
    assert filtered.sizes["station_id"] > 0
    assert (filtered.latitude >= 25).all()
    assert (filtered.latitude <= 45).all()
    assert (filtered.longitude >= -80).all()
    assert (filtered.longitude <= -65).all()


def test_list_available_returns_live_historical_file_index():
    available = xndbc.list_available(mode="stdmet")

    assert isinstance(available, xr.Dataset)
    assert {"station_id", "mode", "year", "url"}.issubset(available.data_vars)
    assert available.sizes["file"] > 0
    assert (available["mode"] == "stdmet").all()


def test_get_stations_extracts_live_station_coordinates():
    stations = station_metadata.get_stations()

    assert isinstance(stations, xr.Dataset)
    assert "latitude" in stations.coords
    assert "longitude" in stations.coords
    assert stations.latitude.sel(station_id="buzm3").item() == 41.397


def test_fetch_data_returns_live_historical_observations():
    data = xndbc.fetch_data("tplm2", years=2020, sample_rate="D")

    assert isinstance(data, xr.Dataset)
    assert data.sizes["station_id"] == 1
    assert data.sizes["time"] > 0
    assert {"latitude", "longitude"}.issubset(data.coords)
    assert len(data.data_vars) > 0
