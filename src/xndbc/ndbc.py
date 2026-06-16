"""NOAA NDBC index, table parsing, and observation retrieval."""

from functools import lru_cache
from io import StringIO
import concurrent.futures
import gzip
import re
from typing import Optional
from urllib.request import urlopen

import numpy as np
import pandas as pd
from tqdm import tqdm
import xarray as xr

HISTORICAL_ROOT = "https://www.ndbc.noaa.gov/data/historical"
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


def read_url_text(url: str) -> str:
    """Read a NOAA NDBC text or gzipped text URL."""
    with urlopen(url, timeout=30) as response:
        raw = response.read()
    if url.endswith(".gz"):
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", errors="ignore")


@lru_cache(maxsize=1)
def historical_modes() -> list[str]:
    """List historical NDBC data modes from the historical directory index."""
    return sorted(
        mode
        for mode in re.findall(r'href="([^"/]+)/"', read_url_text(f"{HISTORICAL_ROOT}/"))
        if mode != ".."
    )


def parse_historical_filename(filename: str, mode: str) -> Optional[dict]:
    """Parse station and year from an NDBC historical filename."""
    if not filename.endswith(".txt.gz"):
        return None
    stem = filename.removesuffix(".txt.gz")
    if len(stem) < 6 or not stem[-4:].isdigit() or not stem[-5].isalpha():
        return None
    return {
        "station_id": stem[:-5].lower(),
        "mode": mode,
        "year": int(stem[-4:]),
        "filename": filename,
    }


@lru_cache(maxsize=None)
def historical_mode_index(mode: str) -> pd.DataFrame:
    """Index historical files available for one NDBC data mode."""
    mode = mode.lower()
    url = f"{HISTORICAL_ROOT}/{mode}/"
    rows = []
    for filename in re.findall(r'href="([^"]+\.txt\.gz)"', read_url_text(url)):
        row = parse_historical_filename(filename, mode)
        if row is not None:
            row["url"] = f"{url}{filename}"
            rows.append(row)
    return pd.DataFrame(rows)


def historical_index(modes: Optional[list[str]] = None) -> pd.DataFrame:
    """Index historical files available across NDBC data modes."""
    modes = historical_modes() if modes is None else modes
    modes = [modes] if isinstance(modes, str) else modes
    frames = [historical_mode_index(mode).copy() for mode in modes]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame(columns=["station_id", "mode", "year", "filename", "url"])
    return pd.concat(frames, ignore_index=True)


def list_available(mode: Optional[str] = "stdmet") -> xr.Dataset:
    """List available historical files as an xarray dataset."""
    available = historical_index(None if mode is None else [mode.lower()])
    if available.empty:
        available = pd.DataFrame(columns=["station_id", "mode", "year", "filename", "url"])
    available = available.reset_index(drop=True)
    available.index.name = "file"
    return available.to_xarray()


def historical_url(station_id: str, year: int, mode: str = "stdmet") -> str:
    """Return the historical data URL for a station, year, and mode."""
    mode = mode.lower()
    available = historical_index([mode])
    matches = available[
        (available["station_id"] == str(station_id).lower())
        & (available["year"] == int(year))
    ]
    if matches.empty:
        raise ValueError(f"No historical {mode} file found for station {station_id}, year {year}")
    return matches.iloc[0]["url"]


def realtime_url(station_id: str, mode: str = "stdmet") -> str:
    """Return the realtime data URL for a station and mode."""
    mode = mode.lower()
    if mode not in REALTIME_EXTENSIONS:
        raise ValueError(f"Unsupported realtime mode: {mode}")
    return f"{REALTIME_ROOT}/{station_id.upper()}.{REALTIME_EXTENSIONS[mode]}"


def read_ndbc_table_from_text(body: str, mode: str = "stdmet") -> pd.DataFrame:
    """Read an NDBC whitespace-delimited observation table from response text."""
    header, data = [], []
    for line in body.splitlines():
        if line.startswith("#"):
            header.append(line)
        elif line.strip():
            data.append(line)
    if not data:
        return pd.DataFrame()

    names = [name for name in header[0].strip("#").split() if name] if header else None
    if names is None and any(char.isalpha() for char in data[0]):
        names, data = data[0].split(), data[1:]
    row_width = len(data[0].split())
    if names is not None and len(names) != row_width:
        if mode.lower() in {"adcp", "adcp2"} and len(names) >= 5 and row_width > 5:
            bins = range(1, ((row_width - 5) // 3) + 1)
            names = names[:5] + [f"{name}{bin_number:02d}" for bin_number in bins for name in ("DEP", "DIR", "SPD")]
        else:
            names = None

    return pd.read_csv(
        StringIO("\n".join(data)),
        sep=r"\s+",
        header=None,
        names=names,
        na_values=NA_VALUES.get(mode.lower(), ["MM"]),
    )


def read_ndbc_table(url: str, mode: str = "stdmet") -> pd.DataFrame:
    """Read an NDBC whitespace-delimited observation table from a URL."""
    return read_ndbc_table_from_text(read_url_text(url), mode=mode)


def timestamped_dataframe(sdf: pd.DataFrame) -> pd.DataFrame:
    """Normalize NDBC date columns and return a time-indexed dataframe."""
    sdf = sdf.rename(
        columns={
            "YY": "year",
            "#YY": "year",
            "YYYY": "year",
            "#YYYY": "year",
            "MM": "month",
            "DD": "day",
            "hh": "hour",
            "mm": "minute",
        }
    )
    sdf["minute"] = 0 if "minute" not in sdf.columns else sdf["minute"]
    sdf["hour"] = 1 if "hour" not in sdf.columns else sdf["hour"]
    sdf["year"] = pd.to_numeric(sdf["year"], errors="coerce")
    sdf["year"] = np.where(sdf["year"] < 100, 1900 + sdf["year"], sdf["year"])
    sdf["time"] = pd.to_datetime(sdf[["year", "month", "day", "hour", "minute"]])
    return sdf.drop(columns=["year", "month", "day", "hour", "minute"]).set_index("time").sort_index()


def adcp_dataset(sdf: pd.DataFrame) -> xr.Dataset:
    """Reshape ADCP DEP/DIR/SPD columns onto a depth_bin dimension."""
    groups = {"DEP": {}, "DIR": {}, "SPD": {}}
    for column in sdf.columns:
        match = re.match(r"^(DEP|DIR|SPD)(\d+)$", str(column))
        if match is not None:
            variable, bin_number = match.groups()
            groups[variable][int(bin_number)] = column

    bins = sorted({bin_number for columns in groups.values() for bin_number in columns})
    if not bins:
        return sdf.to_xarray()

    data_vars = {}
    for variable, columns in groups.items():
        if columns:
            values = np.full((len(sdf.index), len(bins)), np.nan)
            for j, bin_number in enumerate(bins):
                if bin_number in columns:
                    values[:, j] = pd.to_numeric(sdf[columns[bin_number]], errors="coerce")
            data_vars[variable] = (("time", "depth_bin"), values)
    return xr.Dataset(data_vars, coords={"time": sdf.index, "depth_bin": bins})


def spectral_dataset(sdf: pd.DataFrame, mode: str) -> xr.Dataset:
    """Reshape spectral wave columns onto a frequency dimension."""
    columns = []
    for column in sdf.columns:
        try:
            columns.append((float(str(column)), column))
        except ValueError:
            pass
    if not columns:
        return sdf.to_xarray()

    columns = sorted(columns)
    frequencies = [frequency for frequency, _ in columns]
    names = [name for _, name in columns]
    return xr.Dataset(
        {mode: (("time", "frequency"), sdf[names].apply(pd.to_numeric, errors="coerce").to_numpy())},
        coords={"time": sdf.index, "frequency": frequencies},
    )


def observation_dataset(sdf: pd.DataFrame, mode: str, sample_rate: str) -> xr.Dataset:
    """Convert an NDBC observation table to a mode-aware xarray dataset."""
    mode = mode.lower()
    sdf = timestamped_dataframe(sdf)
    if mode in {"adcp", "adcp2"}:
        dataset = adcp_dataset(sdf)
    elif mode in SPECTRAL_MODES:
        dataset = spectral_dataset(sdf, mode)
    else:
        dataset = sdf.to_xarray()
    dataset = dataset.sortby("time").resample(time=SAMPLE_RATE_ALIASES.get(sample_rate, sample_rate)).mean("time")
    return uppercase_data_vars(dataset)


def uppercase_data_vars(dataset: xr.Dataset) -> xr.Dataset:
    """Normalize observation variable names before merge operations."""
    return dataset.rename({name: str(name).upper() for name in dataset.data_vars})


def extract_historical_year(
    yr: int,
    station_id: str = "tplm2",
    sample_rate: str = "D",
    display_error: bool = False,
    mode: str = "stdmet",
) -> Optional[xr.Dataset]:
    """Extract and process historical data for one station/year/mode."""
    try:
        mode = mode.lower()
        table = read_ndbc_table(historical_url(station_id, yr, mode), mode=mode)
        if mode == "stdmet" and "WTMP" not in table.columns and display_error:
            print(f"WTMP not found for station {station_id}, year {yr}")
        return observation_dataset(table, mode, sample_rate)
    except Exception as error:
        if display_error:
            print(f"Error extracting data for station {station_id}, year {yr}: {error}")
        return None


def extract_realtime(
    station_id: str = "tplm2",
    sample_rate: str = "H",
    display_error: bool = False,
    mode: str = "stdmet",
) -> Optional[xr.Dataset]:
    """Extract and process recent realtime data for one station/mode."""
    try:
        mode = mode.lower()
        return observation_dataset(read_ndbc_table(realtime_url(station_id, mode), mode=mode), mode, sample_rate)
    except Exception as error:
        if display_error:
            print(f"Error extracting realtime data for station {station_id}: {error}")
        return None


def get_station_records(
    station_list: list[str],
    years: Optional[list[int]] = None,
    sample_rate: str = "D",
    data_type: str = "historical",
    mode: str | list[str] = "stdmet",
    max_workers: int = 6,
) -> xr.Dataset:
    """Retrieve and combine NDBC records for stations, years, and modes."""
    data_type = data_type.lower()
    if isinstance(mode, list):
        fetch_mode = lambda single_mode: get_station_records(
            station_list, years, sample_rate, data_type, single_mode, max_workers
        )
        datasets = [dataset for dataset in map(fetch_mode, mode) if dataset.data_vars]
        return xr.merge(datasets, compat="override", join="outer") if datasets else xr.Dataset()

    if data_type not in {"historical", "realtime"}:
        raise ValueError("data_type must be 'historical' or 'realtime'")
    if data_type == "historical" and years is None:
        raise ValueError("years is required when data_type='historical'")

    station_datasets = []
    for station_id in tqdm(station_list, desc="Fetching stations", unit="station"):
        if data_type == "realtime":
            results = [extract_realtime(station_id, sample_rate, mode=mode)]
        else:
            fetch_year = lambda yr: extract_historical_year(yr, station_id, sample_rate, mode=mode)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = list(executor.map(fetch_year, years))

        results = [result for result in results if result is not None]
        if not results:
            continue
        results = [uppercase_data_vars(result) for result in results]
        dataset = results[0].sortby("time") if len(results) == 1 else xr.concat(results, dim="time").sortby("time")
        dataset = dataset.drop_duplicates("time").assign_coords(station_id=station_id).expand_dims("station_id")
        station_datasets.append(dataset)

    return xr.merge(station_datasets, compat="no_conflicts", join="outer") if station_datasets else xr.Dataset()
