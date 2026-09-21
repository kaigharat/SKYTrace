"""SkyTrace data modules: loader, audit, cleaning, deduplication, leakage, splitting, schema."""

from .schema import (
    CANONICAL_SCHEMA,
    CANONICAL_DTYPES,
    FUTURE_DERIVED_FIELDS,
    validate_schema,
    coerce_to_canonical,
)

__all__ = [
    "CANONICAL_SCHEMA",
    "CANONICAL_DTYPES",
    "FUTURE_DERIVED_FIELDS",
    "validate_schema",
    "coerce_to_canonical",
]
