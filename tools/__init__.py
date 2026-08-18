"""Build scripts for the case deliverables.

A package only so the tests can import the builders and assert that the deck's
content stays wired to :mod:`auroracart.analysis`. Both modules are meant to be
run as scripts:

    python tools/build_figures.py    # charts -> deliverables/figures/*.png
    python tools/build_deck.py       # those charts + computed facts -> the .pptx
"""
