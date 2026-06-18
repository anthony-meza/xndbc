"""Shared NDBC table parsing and station record assembly."""

from io import StringIO
import gzip
import re
from urllib.request import urlopen

import numpy as np
import pandas as pd
import xarray as xr

NA_VALUES = {
    "adcp": None,
    "adcp2": None,
    "spec": ["N/A"],
    "stdmet": ["MM", 99.0, 999, 9999, 9999.0],
    "cwind": [99.0, 999, 9999, 9999.0, "MM"],
    "supl": [99.0, 999, 999.0, 9999, 9999.0, "MM"],
    "swden": [99.0, 999, 999.0, 9999, 9999.0, "MM"],
    "swdir": [99.0, 999, 999.0, 9999, 9999.0, "MM"],
    "swdir2": [99.0, 999, 999.0, 9999, 9999.0, "MM"],
    "swr1": [99.0, 999, 999.0, 9999, 9999.0, "MM"],
    "swr2": [99.0, 999, 999.0, 9999, 9999.0, "MM"],
}
SAMPLE_RATE_ALIASES = {"H": "h", "M": "ME"}
SPECTRAL_MODES = {"swden", "swdir", "swdir2", "swr1", "swr2"}
ADCP_COLUMNS = ("DEP", "DIR", "SPD")
TIME_COLUMN_NAMES = {
    "YY": "year",
    "#YY": "year",
    "YYYY": "year",
    "#YYYY": "year",
    "MM": "month",
    "DD": "day",
    "hh": "hour",
    "mm": "minute",
}
TIME_COLUMNS = tuple(TIME_COLUMN_NAMES)


def _read_noaa_text(url: str) -> str:
    """Read a plain or gzipped NOAA text URL."""
    with urlopen(url, timeout=30) as response:
        raw = response.read()
    if url.endswith(".gz"):
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", errors="ignore")


def _parse_observation_table(body: str, mode: str = "stdmet") -> pd.DataFrame:
    """Read an NDBC whitespace-delimited observation table."""
    header = [line for line in body.splitlines() if line.startswith("#")]
    data = [line for line in body.splitlines() if line.strip() and not line.startswith("#")]
    if not data:
        return pd.DataFrame()

    names = [name for name in header[0].lstrip("#").split() if name] if header else None
    if names is None and any(char.isalpha() for char in data[0]):
        names, data = data[0].split(), data[1:]
    if names is not None and len(names) != len(data[0].split()):
        # Some ADCP files publish stale headers with fewer bins than the rows.
        if mode.lower() in {"adcp", "adcp2"}:
            time_columns = [name for name in names if name in TIME_COLUMNS]
            data_column_count = len(data[0].split()) - len(time_columns)
            bin_count = data_column_count // len(ADCP_COLUMNS)
            names = time_columns + [f"{name}{i:02d}" for i in range(1, bin_count + 1) for name in ADCP_COLUMNS]
        else:
            names = None

    return pd.read_csv(
        StringIO("\n".join(data)),
        sep=r"\s+",
        names=names,
        na_values=NA_VALUES.get(mode.lower(), ["MM"]),
    )


def _read_observation_table(url: str, mode: str = "stdmet") -> pd.DataFrame:
    """Read an NDBC table from a URL."""
    return _parse_observation_table(_read_noaa_text(url), mode=mode)


def _time_index_observations(df: pd.DataFrame) -> pd.DataFrame:
    """Return observations indexed by normalized NDBC timestamp columns."""
    df = df.rename(columns=TIME_COLUMN_NAMES)
    df = df.assign(
        minute=df["minute"] if "minute" in df else 0,
        hour=df["hour"] if "hour" in df else 1,
        year=lambda x: pd.to_numeric(x["year"], errors="coerce"),
    )
    df["year"] = np.where(df["year"] < 100, 1900 + df["year"], df["year"])
    df["time"] = pd.to_datetime(df[["year", "month", "day", "hour", "minute"]])
    return df.drop(columns=["year", "month", "day", "hour", "minute"]).set_index("time").sort_index()


def _adcp_table_to_dataset(df: pd.DataFrame) -> xr.Dataset:
    """Reshape ADCP DEP/DIR/SPD columns onto a depth bin dimension."""
    bins = sorted(int(str(column).removeprefix("DEP")) for column in df.columns if str(column).startswith("DEP"))
    if not bins:
        return df.to_xarray()

    variables = {}
    for name in ADCP_COLUMNS:
        cols = [f"{name}{bin_id:02d}" for bin_id in bins]
        if any(col in df for col in cols):
            variables[name] = (("time", "depth_bin"), df.reindex(columns=cols).apply(pd.to_numeric).to_numpy())
    return xr.Dataset(variables, coords={"time": df.index, "depth_bin": bins})


def _spectral_table_to_dataset(df: pd.DataFrame, mode: str) -> xr.Dataset:
    """Reshape spectral wave columns onto a frequency dimension."""
    columns = pd.to_numeric(pd.Index(df.columns), errors="coerce")
    names = df.columns[columns.notna()]
    if names.empty:
        return df.to_xarray()
    frequencies = columns[columns.notna()].astype(float)
    return xr.Dataset(
        {mode: (("time", "frequency"), df[names].apply(pd.to_numeric).to_numpy())},
        coords={"time": df.index, "frequency": frequencies},
    )


def _table_to_dataset(df: pd.DataFrame, mode: str, sample_rate: str) -> xr.Dataset:
    """Convert an NDBC table to a resampled ``xarray.Dataset``."""
    mode = mode.lower()
    df = _time_index_observations(df)
    if mode in {"adcp", "adcp2"}:
        dataset = _adcp_table_to_dataset(df)
    elif mode in SPECTRAL_MODES:
        dataset = _spectral_table_to_dataset(df, mode)
    else:
        dataset = df.to_xarray()

    dataset = dataset.rename({name: str(name).upper() for name in dataset.data_vars})
    return dataset.sortby("time").resample(time=SAMPLE_RATE_ALIASES.get(sample_rate, sample_rate)).mean("time")
