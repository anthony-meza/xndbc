from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("nbdc")
except PackageNotFoundError:
    __version__ = "0.1.0"

from .core import (
    list_available,
    fetch_data,
)

__all__ = [
    "list_available",      # List stations or historical file availability
    "fetch_data",          # Download buoy data
]
