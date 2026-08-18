"""AuroraCart at a Crossroads — analysis package for the case study.

Module map (import from here, not from file paths):

* :mod:`auroracart.paths`      — where the data, assets and outputs live.
* :mod:`auroracart.data_prep`  — the one cleaning + feature-engineering pipeline.
* :mod:`auroracart.viz_theme`  — the shared Plotly palette and chart chrome.
* :mod:`auroracart.analysis`   — the case-question metrics (driver ranking,
  Accelerate 2.0 / logistics event windows, the misleading-vs-honest pair).
* :mod:`auroracart.responsive` — browser profile -> figure adaptation.
* :mod:`auroracart.dashboard`  — Deliverable A, the five-tab Dash app.
"""

from auroracart.data_prep import kpi_summary, load_data
from auroracart.paths import PROJECT_ROOT, RAW_DATA_PATH

__all__ = ["load_data", "kpi_summary", "PROJECT_ROOT", "RAW_DATA_PATH"]

__version__ = "1.0.0"
