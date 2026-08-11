"""CPAS-Core v2 reference implementation.

The package demonstrates protocol mechanics. It is not a production security,
authorization, distributed persistence, or model-runtime implementation.
"""

from .identity import identity_digest, identity_projection
from .idp import load_idp, migrate_idp_v1_to_v2, validate_idp

__all__ = [
    "identity_digest",
    "identity_projection",
    "load_idp",
    "migrate_idp_v1_to_v2",
    "validate_idp",
]

__version__ = "2.0.0.dev1"
