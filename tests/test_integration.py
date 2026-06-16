"""
Tests for nbdc package.

Tests cover the main user-facing API as well as individual module functionality.
"""

import pytest
import xarray as xr
import pandas as pd
import numpy as np
import sys
from pathlib import Path

import nbdc
from nbdc import station_metadata

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from helpers import assign_station_locations, compute_data_coverage

pytestmark = pytest.mark.integration


class TestCoreAPI:
    """Test the high-level user-facing API."""

    def test_list_available_mode_none_returns_stations(self):
        """Test listing all stations."""
        stations = nbdc.list_available(mode=None)

        assert isinstance(stations, xr.Dataset)
        assert "latitude" in stations.coords
        assert "longitude" in stations.coords
        assert len(stations.station_id) > 0

    def test_list_available(self):
        """Test listing historical file availability."""
        available = nbdc.list_available(mode="stdmet")

        assert isinstance(available, xr.Dataset)
        assert {"station_id", "mode", "year", "url"}.issubset(available.data_vars)
        assert available.sizes["file"] > 0
        assert (available["mode"] == "stdmet").all()

    def test_station_listing_is_xarray_only(self):
        """Test station listing always returns an xarray Dataset."""
        stations = nbdc.list_available(mode=None)

        assert isinstance(stations, xr.Dataset)
        assert "latitude" in stations.coords
        assert "longitude" in stations.coords

    def test_list_available_mode_none_filters_by_bounds(self):
        """Station discovery can be geographically bounded."""
        filtered = nbdc.list_available(mode=None, lon_min=-80, lon_max=-65, lat_min=25, lat_max=45)

        assert isinstance(filtered, xr.Dataset)
        assert (filtered.latitude >= 25).all()
        assert (filtered.latitude <= 45).all()


class TestStationMetadata:
    """Test station metadata functions."""

    def test_get_station_metadata(self):
        """Test fetching detailed buoy metadata."""
        metadata = station_metadata.get_station_metadata()

        assert isinstance(metadata, xr.Dataset)
        assert metadata.sizes["station_id"] > 0
        assert "LOCATION" in metadata.data_vars
        assert "NOTE" in metadata.data_vars
        assert "buzm3" in metadata.station_id.values

    def test_get_stations(self):
        """Test getting simplified station information."""
        stations = station_metadata.get_stations()

        assert isinstance(stations, xr.Dataset)
        assert "latitude" in stations.coords
        assert "longitude" in stations.coords
        assert stations.latitude.sel(station_id="buzm3").item() == 41.397


class TestDataProcessing:
    """Test data processing functions."""

    def test_compute_data_coverage_returns_standalone_dataset(self):
        """Coverage returns a standalone dataset and leaves inputs unchanged."""
        ds = xr.Dataset({
            "WTMP": (["station_id", "time"], np.random.rand(3, 10)),
            "WSPD": (["station_id", "time"], np.random.rand(3, 10)),
            "station_id": ["A", "B", "C"],
            "time": pd.date_range("2020-01-01", periods=10),
            "latitude": ("station_id", [40.0, 41.0, 42.0]),
            "longitude": ("station_id", [-70.0, -71.0, -72.0]),
        })
        ds = ds.set_coords(["latitude", "longitude"])
        original = ds.copy(deep=True)

        ds["WTMP"].values[0, 0:5] = np.nan  # 50% coverage for station A
        original["WTMP"].values[0, 0:5] = np.nan

        result = compute_data_coverage(ds)

        xr.testing.assert_identical(ds, original)
        assert "WTMP_coverage" in result.data_vars
        assert "WSPD_coverage" in result.data_vars
        assert "latitude" in result.coords
        assert "longitude" in result.coords
        assert result["WTMP_coverage"].sel(station_id="A").values == 50.0
        assert result["WTMP_coverage"].sel(station_id="B").values == 100.0

    def test_compute_data_coverage(self):
        """Test coverage for all time-dependent variables."""
        # Create a simple test dataset
        ds = xr.Dataset({
            "WSPD": (["station_id", "time"], np.random.rand(2, 10)),
            "station_name": ("station_id", ["A", "B"]),
            "station_id": ["A", "B"],
            "time": pd.date_range("2020-01-01", periods=10)
        })

        result = compute_data_coverage(ds)

        assert "WSPD_coverage" in result.data_vars
        assert "station_name_coverage" not in result.data_vars
        assert (result["WSPD_coverage"] == 100.0).all()

    def test_assign_station_locations_overrides_missing_metadata(self):
        ds = xr.Dataset(
            coords={
                "station_id": ["buzm3", "46254"],
                "latitude": ("station_id", [np.nan, 32.868]),
                "longitude": ("station_id", [np.nan, -117.267]),
            }
        )

        result = assign_station_locations(
            ds,
            {"buzm3": {"latitude": 41.397, "longitude": -71.033}},
        )

        assert result.latitude.sel(station_id="buzm3").item() == 41.397
        assert result.longitude.sel(station_id="buzm3").item() == -71.033
        assert result.longitude.sel(station_id="46254").item() == -117.267


class TestPackageImports:
    """Test that main package imports work correctly."""

    def test_version_available(self):
        """Test that package version is accessible."""
        assert hasattr(nbdc, "__version__")
        assert isinstance(nbdc.__version__, str)

    def test_core_functions_available(self):
        """Test that core API functions are available at package level."""
        assert hasattr(nbdc, "list_available")
        assert hasattr(nbdc, "fetch_data")

    def test_small_public_api(self):
        """Test that internals are not exported at package level."""
        assert not hasattr(nbdc, "compute_data_coverage")
        assert not hasattr(nbdc, "filter_by_region")
        assert not hasattr(nbdc, "plot_stations")
        assert not hasattr(nbdc, "get_buoy_metadata")
        assert not hasattr(nbdc, "box_filter_buoys")
        assert not hasattr(nbdc, "extract_historical_year")
        assert not hasattr(nbdc, "list_stations")
