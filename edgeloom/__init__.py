"""EdgeLoom: an open toolchain for validating, patching, and translating
smart-home edge drivers across platforms.

The package bundles three previously separate tools behind one entrypoint:

``patch``      rewrite a SmartThings Edge driver so it exposes device attributes
               the stock distribution hides (``auto_patch``)
``translate``  project Home Assistant entities onto SmartThings Edge profiles
               (``ha2st_edge``, contributed as the translator component)
``discover``   enumerate drivers and fingerprints from a catalog (``discovery``)
``validate``   check profiles and capability maps against the published schema

``validate`` is the assurance layer the other three converge on: whatever path
produced a profile, it has to satisfy the same contract.
"""

__version__ = "0.1.1"

__all__ = ["__version__"]
