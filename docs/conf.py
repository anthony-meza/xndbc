project = "xndbc"
author = "Anthony Meza"

extensions = ["myst_nb"]
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "myst-nb",
    ".ipynb": "myst-nb",
}
master_doc = "index"
exclude_patterns = ["_build"]
html_theme = "sphinx_rtd_theme"
nb_execution_mode = "force"
nb_execution_startup_code = "import xarray as xr\nxr.set_options(display_style='html')"
