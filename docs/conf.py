from pathlib import Path
import shutil

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


HERE = Path(__file__).resolve()
DOCS_SOURCE = HERE.parent
REPO_ROOT = HERE.parent.parent
EXAMPLES_SRC = REPO_ROOT / "examples"
EXAMPLES_DST = DOCS_SOURCE / "examples"


def _sync_examples():
    if not EXAMPLES_SRC.exists():
        return

    if EXAMPLES_DST.exists():
        shutil.rmtree(EXAMPLES_DST)
    EXAMPLES_DST.mkdir(parents=True, exist_ok=True)

    for notebook in EXAMPLES_SRC.rglob("*.ipynb"):
        target = EXAMPLES_DST / notebook.relative_to(EXAMPLES_SRC)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(notebook, target)


_sync_examples()
