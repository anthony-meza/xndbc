"""
Basic tests for xndbc package that don't require network access.
"""

import pytest
import xarray as xr
import pandas as pd
import numpy as np
import sys
from pathlib import Path

import xndbc
from xndbc import ndbc

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from helpers import assign_station_locations, compute_data_coverage


class TestPackageStructure:
    """Test that the package is properly structured."""

    def test_version_available(self):
        """Test that package version is accessible."""
        assert hasattr(xndbc, "__version__")
        assert isinstance(xndbc.__version__, str)

    def test_core_functions_available(self):
        """Test that core API functions are available at package level."""
        assert hasattr(xndbc, "list_available")
        assert hasattr(xndbc, "fetch_data")

    def test_small_public_api(self):
        """Test that the package-level namespace stays focused."""
        assert not hasattr(xndbc, "compute_data_coverage")
        assert not hasattr(xndbc, "filter_by_region")
        assert not hasattr(xndbc, "plot_stations")
        assert not hasattr(xndbc, "extract_historical_year")
        assert not hasattr(xndbc, "historical_index")
        assert not hasattr(xndbc, "box_filter_buoys")
        assert not hasattr(xndbc, "list_stations")


class TestDataProcessing:
    """Test data processing functions without network access."""

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

    def test_compute_data_coverage_skips_non_time_variables(self):
        """Coverage is computed for all time-dependent variables."""
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
        assert result.latitude.sel(station_id="46254").item() == 32.868


class TestNdbcParsingWorkflows:
    """Test representative NDBC table-to-xarray conversions."""

    def test_stdmet_table_becomes_time_dataset(self):
        body = """
#YY MM DD hh mm WDIR WSPD WTMP
#yr mo dy hr mn degT m/s degC
20 01 01 00 00 180 5.0 20.1
20 01 01 01 00 190 6.0 MM
"""
        table = ndbc.read_ndbc_table_from_text(body, mode="stdmet")
        ds = ndbc.observation_dataset(table, mode="stdmet", sample_rate="H")

        assert set(["WDIR", "WSPD", "WTMP"]).issubset(ds.data_vars)
        assert ds.sizes["time"] == 2
        assert np.isnan(ds["WTMP"].isel(time=1).item())

    def test_legacy_stdmet_header_becomes_time_dataset(self):
        body = """
YY MM DD hh WD WSPD GST WVHT DPD APD MWD BAR ATMP WTMP
98 01 01 00 180 5.0 6.0 1.0 10.0 7.0 270 1010.0 12.0 13.0
98 01 01 01 190 6.0 7.0 1.2 11.0 7.5 280 1011.0 12.5 13.2
"""
        table = ndbc.read_ndbc_table_from_text(body, mode="stdmet")
        ds = ndbc.observation_dataset(table, mode="stdmet", sample_rate="D")

        assert {"WD", "WSPD", "WTMP"}.issubset(ds.data_vars)
        assert ds.sizes["time"] == 1
        assert ds["WTMP"].isel(time=0).item() == 13.1

    def test_adcp_table_becomes_depth_bin_dataset(self):
        body = """
#YY MM DD hh mm DEP01 DIR01 SPD01 DEP02 DIR02 SPD02
#yr mo dy hr mn m deg cm/s m deg cm/s
20 01 01 00 00 5 180 10 10 190 20
20 01 01 01 00 5 181 11 10 191 21
"""
        table = ndbc.read_ndbc_table_from_text(body, mode="adcp")
        ds = ndbc.observation_dataset(table, mode="adcp", sample_rate="H")

        assert set(["DEP", "DIR", "SPD"]).issubset(ds.data_vars)
        assert ds.sizes["time"] == 2
        assert ds.sizes["depth_bin"] == 2
        assert ds["SPD"].sel(depth_bin=2).isel(time=1).item() == 21

    def test_adcp_table_extends_stale_header_bins(self):
        body = """
#YY MM DD hh mm DEP01 DIR01 SPD01
#yr mo dy hr mn m deg cm/s
2020 01 01 00 00 5 180 10 10 190 20
2020 01 01 01 00 5 181 11 10 191 21
"""
        table = ndbc.read_ndbc_table_from_text(body, mode="adcp")
        ds = ndbc.observation_dataset(table, mode="adcp", sample_rate="H")

        assert ds.sizes["depth_bin"] == 2
        assert ds["SPD"].sel(depth_bin=2).isel(time=1).item() == 21

    def test_spectral_table_becomes_frequency_dataset(self):
        body = """
#YY MM DD hh mm .0200 .0325 .0375
#yr mo dy hr mn Hz Hz Hz
2020 01 01 00 00 1.0 2.0 3.0
2020 01 01 01 00 1.5 2.5 3.5
"""
        table = ndbc.read_ndbc_table_from_text(body, mode="swden")
        ds = ndbc.observation_dataset(table, mode="swden", sample_rate="H")

        assert "SWDEN" in ds.data_vars
        assert ds.sizes["frequency"] == 3
        assert ds["SWDEN"].sel(frequency=0.0325).isel(time=0).item() == 2.0

    def test_fetch_data_can_merge_multiple_modes(self, monkeypatch):
        def fake_extract_historical_year(yr, station_id, sample_rate, mode, display_error=False):
            time = pd.date_range(f"{yr}-01-01", periods=2, freq="h")
            if mode == "stdmet":
                return xr.Dataset({"WTMP": ("time", [20.0, 21.0])}, coords={"time": time})
            if mode == "swden":
                return xr.Dataset(
                    {"swden": (("time", "frequency"), [[1.0, 2.0], [1.5, 2.5]])},
                    coords={"time": time, "frequency": [0.02, 0.0325]},
                )
            return xr.Dataset()

        monkeypatch.setattr(
            ndbc,
            "extract_historical_year",
            fake_extract_historical_year,
        )

        monkeypatch.setattr(
            "xndbc.core.get_stations",
            lambda: xr.Dataset(
                coords={
                    "station_id": ["41001"],
                    "latitude": ("station_id", [40.0]),
                    "longitude": ("station_id", [-70.0]),
                }
            ),
        )

        ds = xndbc.fetch_data("41001", years=2020, mode=["stdmet", "swden"])

        assert {"WTMP", "SWDEN"}.issubset(ds.data_vars)
        assert ds.sizes["station_id"] == 1
        assert ds.sizes["frequency"] == 2
        assert "latitude" in ds.coords
        assert "longitude" in ds.coords
        assert "latitude" not in ds.data_vars

    def test_variable_names_are_uppercase_before_merge(self, monkeypatch):
        def fake_extract_historical_year(yr, station_id, sample_rate, mode, display_error=False):
            time = pd.date_range(f"{yr}-01-01", periods=1, freq="h")
            return xr.Dataset({"wspd": ("time", [5.0])}, coords={"time": time})

        monkeypatch.setattr(ndbc, "extract_historical_year", fake_extract_historical_year)
        monkeypatch.setattr(
            "xndbc.core.get_stations",
            lambda: xr.Dataset(
                coords={
                    "station_id": ["41001", "41002"],
                    "latitude": ("station_id", [40.0, 41.0]),
                    "longitude": ("station_id", [-70.0, -71.0]),
                }
            ),
        )

        ds = xndbc.fetch_data(["41001", "41002"], years=2020)

        assert "WSPD" in ds.data_vars
        assert "wspd" not in ds.data_vars

    def test_list_available_mode_none_filters_stations_by_bounds(self, monkeypatch):
        monkeypatch.setattr(
            "xndbc.core.get_stations",
            lambda: xr.Dataset(
                coords={
                    "station_id": ["a", "b", "c"],
                    "latitude": ("station_id", [20.0, 40.0, -10.0]),
                    "longitude": ("station_id", [-70.0, -120.0, -50.0]),
                }
            ),
        )

        result = xndbc.list_available(mode=None, lon_min=-80, lon_max=-60, lat_min=10, lat_max=30)

        assert result.station_id.values.tolist() == ["a"]
