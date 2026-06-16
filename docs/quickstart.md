# Quickstart

```python
import xndbc

# List all known stations.
stations = xndbc.list_available(mode=None)

# List stations with historical standard meteorological files.
available = xndbc.list_available(mode="stdmet")

# List stations in a region.
caribbean = xndbc.list_available(
    mode=None,
    lon_min=-85,
    lon_max=-60,
    lat_min=10,
    lat_max=25,
)

# Fetch historical data for specific stations.
data = xndbc.fetch_data(
    station_ids=["42095"],
    years=range(2000, 2021),
    sample_rate="D",
)
```
