# nbdc

`nbdc` is a Python package for accessing and analyzing buoy data distributed by the National Data Buoy Center (NDBC) in `xarray`.

<p align="center">
  <strong>Buoy Temperature Trends (1992-2021) </strong><br>
  <img width="585" src="https://github.com/user-attachments/assets/9a64a9b2-21a4-48b6-8452-36e5807dcc2f">
</p>

## Installation

### Using a Python virtual environment (recommended)

```bash
# Create and activate a virtual environment
$ python -m venv nbdc-env
$ source nbdc-env/bin/activate  # On macOS/Linux
$ nbdc-env\Scripts\activate     # On Windows

# Install nbdc
$ pip install git+https://github.com/anthony-meza/nbdc.git@main
```

## Quick Start

```python
import nbdc

# List all available stations
stations = nbdc.list_available(mode=None)

# List available historical standard meteorological files
available = nbdc.list_available(mode="stdmet")

# List stations in a region
caribbean = nbdc.list_available(
    mode=None,
    lon_min=-85,
    lon_max=-60,
    lat_min=10,
    lat_max=25,
)

# Fetch historical data for specific stations
data = nbdc.fetch_data(
    station_ids=["42095"],
    years=range(2000, 2021),
    sample_rate="D"  # Daily averages
)

# Example notebooks include helper functions for plotting and coverage summaries.
```
Check the `examples/` directory for Jupyter notebooks examples. 


### For developers (using Poetry)

```bash
# Clone the repository
git clone https://github.com/anthony-meza/nbdc.git
cd nbdc

# Install dependencies with Poetry
poetry install

# Build the package
poetry build

# Install locally
pip install ./dist/nbdc-X.X.X-py3-none-any.whl
```

## Contributing

Interested in contributing? Check out the contributing guidelines. Please note that this project is released with a Code of Conduct. By contributing to this project, you agree to abide by its terms.

## License

`nbdc` was created by Anthony Meza. It is licensed under the terms of the MIT license.

## Credits

`nbdc` was created with [`cookiecutter`](https://cookiecutter.readthedocs.io/en/latest/) and the `py-pkgs-cookiecutter` [template](https://github.com/py-pkgs/py-pkgs-cookiecutter).

Development setup follows the [`py-pkgs`](https://py-pkgs.org/03-how-to-package-a-python.html) guide using Poetry for dependency management.
