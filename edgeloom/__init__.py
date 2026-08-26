"""EdgeLoom: an open toolchain for auditing, validating, patching, restoring,
translating, and discovering smart-home edge-driver artifacts.

The package bundles three previously separate tools behind one entrypoint:

``patch``      rewrite a SmartThings Edge driver so it exposes device attributes
               the stock distribution hides (``auto_patch``)
``restore``    return a patched driver to its preserved pre-patch tree
``translate``  project Home Assistant entities onto SmartThings Edge profiles
               (``ha2st_edge``, contributed as the translator component)
``discover``   enumerate drivers and fingerprints from a catalog (``discovery``)
``validate``   check profiles and capability maps against the published schema
``audit``      emit provenance and deterministic-check evidence for a local artifact

``validate`` and ``audit`` provide complementary assurance: one applies a
versioned contract; the other records exactly which bytes, source assertions,
checks, authority labels, and limitations were reviewed.
"""

__version__ = "0.1.1"

__all__ = ["__version__"]
