"""The dashboard imports, finds its assets, and renders every tab.

A Dash app fails loudly at import but silently at render, so each tab renderer
is exercised here — including against a filter selection that matches no orders,
which is the state a live user reaches fastest.
"""

import pandas as pd
import pytest

from auroracart import dashboard as D
from auroracart.responsive import DEFAULT_PROFILE, ViewProfile, profile_from_store


@pytest.fixture(scope="module")
def data() -> pd.DataFrame:
    return D.DF


def test_wsgi_entrypoint_is_importable():
    """`gunicorn app:server` must resolve — this is what Render runs."""
    import app

    assert app.server is D.server


def test_assets_travel_with_the_package():
    from auroracart.paths import ASSETS_DIR

    assert D.app.config.assets_folder == str(ASSETS_DIR)
    for asset in ("style.css", "environment.js", "scroll-hints.js"):
        assert (ASSETS_DIR / asset).exists()


@pytest.mark.parametrize("tab", sorted(D.RENDERERS))
@pytest.mark.parametrize(
    "view", [DEFAULT_PROFILE, profile_from_store({"width": 375, "pointer": "coarse"})]
)
def test_every_tab_renders(data, tab: str, view: ViewProfile):
    assert D.RENDERERS[tab](data, view) is not None


@pytest.mark.parametrize("tab", sorted(D.RENDERERS))
def test_every_tab_survives_an_empty_selection(data, tab: str):
    assert D.RENDERERS[tab](data.iloc[0:0], DEFAULT_PROFILE) is not None


def test_filters_narrow_the_frame(data):
    filtered = D.apply_filters(
        data,
        data["Order_Date"].min(),
        data["Order_Date"].max(),
        regions=["North"],
        categories=["Electronics"],
        segments=None,
        fulfillment=None,
    )
    assert 0 < len(filtered) < len(data)
    assert set(filtered["Region"].unique()) == {"North"}
    assert set(filtered["Category"].unique()) == {"Electronics"}
