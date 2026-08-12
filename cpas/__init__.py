"""CPAS-Core v2 reference implementation.

The package demonstrates protocol mechanics. It is not a production security,
authorization, distributed persistence, or model-runtime implementation.
"""

from .identity import identity_digest, identity_projection
from .governance import (
    classify_declaration_change,
    create_transition_record,
    evaluate_approvals,
    validate_transition,
)
from .idp import (
    load_idp,
    migrate_idp_v1_to_v2,
    migrate_idp_v2_draft_governance,
    validate_idp,
)

__all__ = [
    "identity_digest",
    "identity_projection",
    "classify_declaration_change",
    "create_transition_record",
    "evaluate_approvals",
    "load_idp",
    "migrate_idp_v1_to_v2",
    "migrate_idp_v2_draft_governance",
    "validate_idp",
    "validate_transition",
]

__version__ = "2.0.0.dev1"
