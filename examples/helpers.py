import matplotlib.pyplot as plt
import xarray as xr
import cartopy.crs as ccrs
import cartopy.feature as cfeature

def compute_data_coverage(ds):
    coverage = {}
    for name, variable in ds.data_vars.items():
        if "time" in variable.dims:
            coverage[f"{name}_coverage"] = 100 * variable.notnull().sum(dim="time") / ds.sizes["time"]
    return xr.Dataset(coverage)


def assign_station_locations(ds, locations):
    station_ids = [str(station_id) for station_id in ds.station_id.values]
    latitude = [
        locations.get(station_id.lower(), {}).get("latitude", ds.latitude.sel(station_id=station_id).item())
        for station_id in station_ids
    ]
    longitude = [
        locations.get(station_id.lower(), {}).get("longitude", ds.longitude.sel(station_id=station_id).item())
        for station_id in station_ids
    ]
    return ds.assign_coords(latitude=("station_id", latitude), longitude=("station_id", longitude))


def plot_stations(ds, variable=None, ax=None, add_labels = True):


    fig, ax = (
        plt.subplots(figsize=(8, 4), subplot_kw={"projection": ccrs.PlateCarree()})
        if ax is None
        else (ax.figure, ax)
    )
    transform = ccrs.PlateCarree()
    ax.add_feature(cfeature.LAND, facecolor="0.85", edgecolor="0.5", linewidth=0.6)
    ax.coastlines(color="0.5", linewidth=0.6)
    gridlines = ax.gridlines(draw_labels=True, alpha=0.25)
    gridlines.top_labels = False
    gridlines.right_labels = False

    valid_location = ds.latitude.notnull() & ds.longitude.notnull()
    located = ds.where(valid_location, drop=True)
    if variable is None:
        ax.scatter(
            located.longitude,
            located.latitude,
            c="tab:red",
            edgecolors="black",
            linewidths=0.4,
            s=36,
            alpha=0.9,
            transform=transform,
        )
    else:
        has_data = located[variable].notnull()
        missing = located.where(~has_data, drop=True)
        plotted = located.where(has_data, drop=True)
        if missing.sizes.get("station_id", 0):
            ax.scatter(
                missing.longitude,
                missing.latitude,
                c="0.8",
                edgecolors="black",
                linewidths=0.4,
                s=36,
                alpha=0.85,
                label="no data",
                transform=transform,
            )
        scatter = ax.scatter(
            plotted.longitude,
            plotted.latitude,
            c=plotted[variable],
            edgecolors="black",
            linewidths=0.4,
            s=36,
            alpha=0.9,
            transform=transform,
        )
        fig.colorbar(scatter, ax=ax, label=variable)
        if missing.sizes.get("station_id", 0):
            ax.legend()
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(alpha=0.25)

    if add_labels: 
        for station in located.station_id.values:
            row = located.sel(station_id=station)
            ax.annotate(
                str(station).upper(),
                (row.longitude.item(), row.latitude.item()),
                xytext=(3, 3),
                textcoords="offset points",
                fontsize=8,
                fontweight="bold",
                transform=transform,
            )
    return fig, ax
