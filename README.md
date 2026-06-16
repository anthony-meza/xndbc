# xndbc
[![Documentation Status](https://readthedocs.org/projects/xndbc/badge/?version=latest)](https://xndbc.readthedocs.io/en/latest/?badge=latest)

> **Note:** `xndbc` is still in development. APIs, behavior, and documentation may change as the package matures.

`xndbc` provides Python tools for discovering NOAA National Data Buoy Center (NDBC) stations and loading buoy observations into `xarray` objects.

<p align="center">
  <strong>Buoy Temperature Trends (1992-2021) </strong><br>
  <img width="585" src="https://github.com/user-attachments/assets/9a64a9b2-21a4-48b6-8452-36e5807dcc2f">
</p>

## Installation

```bash
pip install git+https://github.com/anthony-meza/xndbc.git@main
```

## Quick Start

```python
import xndbc

# List all available stations
stations = xndbc.list_available(mode=None)

# List available historical standard meteorological files
available = xndbc.list_available(mode="stdmet")

# List stations in a region
caribbean = xndbc.list_available(
    mode=None,
    lon_min=-85,
    lon_max=-60,
    lat_min=10,
    lat_max=25,
)

# Fetch historical data for specific stations
data = xndbc.fetch_data(
    station_ids=["42095"],
    years=range(2000, 2021),
    sample_rate="D"  # Daily averages
)
```

The `examples/` directory contains notebooks with complete workflows for regional station searches, historical data access, realtime data, plotting, and coverage summaries.

## Development

```bash
# Clone the repository
git clone https://github.com/anthony-meza/xndbc.git
cd xndbc

# Create and activate the development environment
conda env create -f docs/environment.yml
conda activate xndbc-dev

# Run the test suite
pytest
```

## Contributing

Interested in contributing? Check out the contributing guidelines. Please note that this project is released with a Code of Conduct. By contributing to this project, you agree to abide by its terms.

## License

`xndbc` was created by Anthony Meza. It is licensed under the terms of the MIT license.

## Credits

`xndbc` was created with [`cookiecutter`](https://cookiecutter.readthedocs.io/en/latest/) and the `py-pkgs-cookiecutter` [template](https://github.com/py-pkgs/py-pkgs-cookiecutter).
