"""EdgeLoom: an open toolchain for auditing, validating, patching, restoring,
translating, and discovering smart-home edge-driver artifacts.

The package exposes six related workflows behind one entrypoint:

``patch``      rewrite a SmartThings Edge driver so it exposes device attributes
               the stock distribution hides (``auto_patch``)
``restore``    return a patched driver to its preserved pre-patch tree
``translate``  project Home Assistant entities onto SmartThings Edge profiles
               (``ha2st_edge``, contributed as the translator component)
``discover``   enumerate drivers and fingerprints from a catalog (``discovery``)
``validate``   check profiles and capability maps against the published schema
``audit``      emit identity and deterministic-check evidence for a local artifact

``validate`` applies versioned contracts; ``audit`` records the exact local byte
snapshot, asserted source metadata, checks, authority labels, and limitations.
"""

__version__ = "0.1.1"

__all__ = ["__version__"]
