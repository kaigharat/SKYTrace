"""Canonical SkyTrace schema.

This module defines the ONE schema that all future DL components (CodeBERT,
GCN/GAT, LSTM, fusion, multi-task, FAISS, explainability) will consume.
Nothing in this phase writes outside this schema, and nothing in future
phases should need to redesign it.

The schema is organised into five blocks:

    1. Identification — sample_id, project, repository, file_path
    2. Code            — function_code, function_name, language
    3. Security        — label, cwe, cve
    4. History         — commit_id, commit_date
    5. Future-derived  — prior_defect_count, prior_vulnerability_count,
                          co_change_frequency, file_volatility

Future-derived fields are explicitly NULL until the repository-mining phase
produces them. They MUST NOT be filled with zeros unless zero is semantically
correct (i.e. the file truly has no prior defects).
"""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

# ----- Schema definition ---------------------------------------------------

# Each field is (name, dtype, nullable, block, description)
CANONICAL_SCHEMA: List[Dict[str, Any]] = [
    # ---- 1. Identification ----
    {"name": "sample_id",     "dtype": "string",  "nullable": False, "block": "identification",
     "description": "Stable unique identifier for the function sample (sha1 of normalised code)."},
    {"name": "project",       "dtype": "string",  "nullable": True,  "block": "identification",
     "description": "Project name (e.g. linux, openssl). Used for leakage-aware splitting."},
    {"name": "repository",    "dtype": "string",  "nullable": True,  "block": "identification",
     "description": "Repository identifier; falls back to project if absent in source."},
    {"name": "file_path",     "dtype": "string",  "nullable": True,  "block": "identification",
     "description": "Path of the file inside the repository."},

    # ---- 2. Code ----
    {"name": "function_code", "dtype": "string",  "nullable": False, "block": "code",
     "description": "Raw C/C++ function source code."},
    {"name": "function_name", "dtype": "string",  "nullable": True,  "block": "code",
     "description": "Function name if extractable from source; else NULL."},
    {"name": "language",      "dtype": "string",  "nullable": False, "block": "code",
     "description": "Programming language. Always 'c' or 'cpp' for DiverseVul."},

    # ---- 3. Security ----
    {"name": "label",         "dtype": "int8",    "nullable": False, "block": "security",
     "description": "1 = vulnerable, 0 = non-vulnerable."},
    {"name": "cwe",           "dtype": "string",  "nullable": True,  "block": "security",
     "description": "CWE identifier (e.g. 'CWE-119'). NULL for non-vulnerable samples."},
    {"name": "cve",           "dtype": "string",  "nullable": True,  "block": "security",
     "description": "CVE identifier if available. NULL otherwise."},

    # ---- 4. History ----
    {"name": "commit_id",     "dtype": "string",  "nullable": True,  "block": "history",
     "description": "Git commit hash the sample was extracted from."},
    {"name": "commit_date",   "dtype": "string",  "nullable": True,  "block": "history",
     "description": "ISO-8601 commit date if recoverable from source. NULL otherwise."},

    # ---- 5. Future-derived (NULL until repository-mining phase) ----
    {"name": "prior_defect_count",        "dtype": "Int64",   "nullable": True, "block": "future_derived",
     "description": "DERIVED. Count of prior defective commits touching this file."},
    {"name": "prior_vulnerability_count", "dtype": "Int64",   "nullable": True, "block": "future_derived",
     "description": "DERIVED. Count of prior vulnerability-fixing commits touching this file."},
    {"name": "co_change_frequency",       "dtype": "float64", "nullable": True, "block": "future_derived",
     "description": "DERIVED. Co-change frequency with other files in the same project."},
    {"name": "file_volatility",           "dtype": "float64", "nullable": True, "block": "future_derived",
     "description": "DERIVED. Historical churn metric for this file."},
]

CANONICAL_FIELDS: List[str] = [f["name"] for f in CANONICAL_SCHEMA]
CANONICAL_DTYPES: Dict[str, str] = {f["name"]: f["dtype"] for f in CANONICAL_SCHEMA}
FUTURE_DERIVED_FIELDS: List[str] = [f["name"] for f in CANONICAL_SCHEMA if f["block"] == "future_derived"]


def validate_schema(df: pd.DataFrame) -> List[str]:
    """Return a list of schema violations. Empty list = schema OK."""
    violations: List[str] = []
    present = set(df.columns)

    for field in CANONICAL_SCHEMA:
        name = field["name"]
        if name not in present:
            if field["block"] == "future_derived":
                # Future-derived fields may be added later; warn but don't fail.
                continue
            violations.append(f"Missing required field: {name}")

    # Non-null checks
    for field in CANONICAL_SCHEMA:
        if field["nullable"]:
            continue
        if field["name"] not in present:
            continue
        if field["block"] == "future_derived":
            continue
        n_null = int(df[field["name"]].isna().sum())
        if n_null > 0:
            violations.append(
                f"Field '{field['name']}' is declared non-nullable but has {n_null} null values"
            )
    return violations


def coerce_to_canonical(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce a dataframe to canonical dtypes without dropping rows.

    Future-derived fields that are not present are added as all-NULL columns
    (pandas NA). This is the SINGLE entry point any loader must call before
    writing parquet.
    """
    out = df.copy()

    # Add missing future-derived columns as NULL — never as zero.
    for field in CANONICAL_SCHEMA:
        if field["block"] == "future_derived" and field["name"] not in out.columns:
            out[field["name"]] = pd.Series(dtype=field["dtype"])

    # Coerce dtypes
    for field in CANONICAL_SCHEMA:
        name = field["name"]
        if name not in out.columns:
            continue
        dtype = field["dtype"]
        try:
            if dtype == "string":
                out[name] = out[name].astype("string")
            elif dtype == "int8":
                # Tolerate float labels coming from parquet round-trips.
                out[name] = out[name].astype("Int64").astype("int8")
            elif dtype == "Int64":
                out[name] = out[name].astype("Int64")
            elif dtype == "float64":
                out[name] = out[name].astype("float64")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Could not coerce column '{name}' to {dtype}: {e}") from e

    # Reorder columns to canonical order
    ordered = [f for f in CANONICAL_FIELDS if f in out.columns]
    extras = [c for c in out.columns if c not in ordered]
    return out[ordered + extras]
