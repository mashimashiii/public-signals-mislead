"""
Configuration module for known business outcomes.

Modules:
    - outcomes: Feature outcomes and classifications
"""

from .outcomes import (
    KNOWN_OUTCOMES,
    FEATURE_TYPES,
    get_outcome,
    get_feature_type,
    get_all_labeled_features,
    get_success_count,
)

__all__ = [
    "KNOWN_OUTCOMES",
    "FEATURE_TYPES",
    "get_outcome",
    "get_feature_type",
    "get_all_labeled_features",
    "get_success_count",
]