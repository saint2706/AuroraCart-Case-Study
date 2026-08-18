"""The deliverable build chain stays wired to the analysis.

These do not re-render PNGs or write a .pptx — that needs a headless browser and
is a build step, not a test. What they guard is the property that matters: the
deck's prose and figures are generated from computed facts, so a slide cannot
quietly disagree with the dataset.
"""

import re

import pytest

from auroracart import analysis as A
from auroracart.data_prep import load_data
from auroracart.paths import DELIVERABLES_DIR, FIGURES_DIR


@pytest.fixture(scope="module")
def facts() -> dict:
    return A.headline_facts(load_data())


def test_every_headline_fact_is_finite(facts):
    for key, value in facts.items():
        if isinstance(value, str):
            continue
        assert value == value, f"{key} is NaN"
        assert abs(value) != float("inf"), f"{key} is infinite"


def test_deck_slides_build_from_facts(facts):
    from tools.build_deck import build_slides

    slides = build_slides(facts)
    assert len(slides) >= 12, "a 7–10 minute deck needs more than a handful of slides"

    kinds = [s.kind for s in slides]
    assert kinds[0] == "title"
    assert "closing" in kinds, "the recommendations slide is the point of the deck"
    assert kinds.count("section") >= 4, "Context/Tension/Investigation/Evidence/Decision arc"


def test_every_deck_figure_exists(facts):
    from tools.build_deck import build_slides

    missing = [
        s.figure for s in build_slides(facts)
        if s.figure and not (FIGURES_DIR / f"{s.figure}.png").exists()
    ]
    assert not missing, f"run tools/build_figures.py — missing {missing}"


def test_speaker_notes_carry_timings(facts):
    """The brief asks for 7–10 minutes; the notes have to be pace-able."""
    from tools.build_deck import build_slides

    timed = [s for s in build_slides(facts) if re.search(r"\[\d+:\d\d", s.notes)]
    assert len(timed) >= 10


def test_figure_builders_are_all_reachable():
    """Each named figure has a builder, so the deck cannot reference a stale name."""
    from tools import build_figures

    assert set(build_figures.FIGURES) == {p.stem for p in FIGURES_DIR.glob("*.png")}


def test_deck_is_committed():
    assert (DELIVERABLES_DIR / "AuroraCart_Executive_Story.pptx").exists()
