"""DiverseVul loader.

Downloads DiverseVul from HuggingFace and maps the raw source columns into the
canonical SkyTrace schema. The loader DOES NOT clean, deduplicate or split —
it only:

    1. Pull the raw dataset (streaming-aware, supports --sample-size)
    2. Inspect the actual columns present
    3. Map them into the canonical schema
    4. Return a pandas DataFrame for downstream audit / cleaning

If a column is missing in source, it is left NULL — never fabricated.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

import pandas as pd
import yaml
from datasets import load_dataset


# ----- Config ---------------------------------------------------------------

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "configs", "dataset.yaml"
)


@dataclass
class LoaderConfig:
    source: str = "bstee615/diversevul"
    hf_revision: Optional[str] = None
    cache_dir: str = "data/raw/diversevul_cache"
    sample_size: Optional[int] = None      # None = full dataset
    raw_dump_path: str = "data/raw/diversevul_raw.parquet"

    @classmethod
    def from_yaml(cls, path: str = DEFAULT_CONFIG_PATH) -> "LoaderConfig":
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        paths = cfg.get("paths", {})
        dataset = cfg.get("dataset", {})
        mode = cfg.get("mode", {})
        return cls(
            source=dataset.get("source", "bstee615/diversevul"),
            hf_revision=dataset.get("hf_revision"),
            cache_dir=paths.get("raw_cache", "data/raw/diversevul_cache"),
            sample_size=mode.get("dev_sample_size") if mode.get("default") == "dev" else None,
            raw_dump_path=os.path.join(paths.get("raw_dir", "data/raw"), "diversevul_raw.parquet"),
        )


# ----- Column mapping -------------------------------------------------------
# DiverseVul has shipped in multiple HF mirrors with slightly different
# column names. We define a *candidate list* per canonical field and pick
# the first one that actually exists in the loaded dataset.

COLUMN_CANDIDATES: Dict[str, list] = {
    "function_code":   ["func", "function", "code", "source_code", "function_code"],
    "label":           ["target", "label", "vulnerable", "is_vulnerable"],
    "project":         ["project", "repo", "repository"],
    "commit_id":       ["commit_id", "commit", "commit_hash"],
    "cve":             ["cve", "cve_id"],
    "cwe":             ["cwe", "cwe_id"],
    "file_path":       ["file", "file_path", "filename", "path"],
    "commit_message":  ["message", "commit_message"],
    "size":            ["size", "length"],
    "hash":            ["hash", "fingerprint"],
}


def _pick(source_cols: list, candidates: list) -> Optional[str]:
    for c in candidates:
        if c in source_cols:
            return c
    return None


# ----- Function-name extraction ---------------------------------------------

_FUNC_NAME_RE = re.compile(
    r"""^[A-Za-z_][A-Za-z0-9_\s\*]*?      # return type & qualifiers
        \b([A-Za-z_][A-Za-z0-9_]*)\s*\(   # function name (captured) + (
    """,
    re.VERBOSE,
)


def extract_function_name(code: str) -> Optional[str]:
    """Best-effort extraction of a C/C++ function name from source.

    Returns None if extraction fails — never fabricates a name.
    """
    if not code or not isinstance(code, str):
        return None
    # Strip preprocessor / comments at the very top
    lines = code.lstrip().splitlines()
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("//") or s.startswith("/*"):
            continue
        m = _FUNC_NAME_RE.match(s)
        if m:
            return m.group(1)
        # single-line function definition
        if "(" in s:
            head = s.split("(", 1)[0].strip()
            tail = head.split()[-1] if head else ""
            tail = tail.lstrip("*")
            if tail and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", tail):
                return tail
        break
    return None


# ----- Sample ID generation -------------------------------------------------

_WS_RE = re.compile(r"\s+")


def _normalise_for_hash(code: str) -> str:
    """Normalise whitespace before hashing so trivial formatting differences
    do NOT count as different functions, but real code differences do."""
    if not isinstance(code, str):
        return ""
    return _WS_RE.sub(" ", code.strip())


def make_sample_id(code: str, project: Optional[str], commit_id: Optional[str]) -> str:
    """Stable per-sample ID.

    Uses sha1 of (normalised_code | project | commit_id). We include project +
    commit so that the *same* code appearing in two different commits is NOT
    collapsed into one sample by the audit phase — but the audit phase will
    still flag the function-code hash as a duplicate.
    """
    h = hashlib.sha1()
    norm = _normalise_for_hash(code)
    h.update(norm.encode("utf-8", errors="ignore"))
    h.update(b"|")
    h.update((project or "").encode("utf-8", errors="ignore"))
    h.update(b"|")
    h.update((commit_id or "").encode("utf-8", errors="ignore"))
    return h.hexdigest()


def make_function_hash(code: str) -> str:
    """Hash ONLY of the normalised code — used for duplicate-function detection."""
    return hashlib.sha1(_normalise_for_hash(code).encode("utf-8", errors="ignore")).hexdigest()


# ----- Main loader ----------------------------------------------------------

def load_diversevul(
    cfg: Optional[LoaderConfig] = None,
    sample_size: Optional[int] = None,
    streaming: bool = False,
) -> pd.DataFrame:
    """Download DiverseVul and return a raw pandas DataFrame mapped to canonical schema.

    The source dataset ships with its own pre-defined train/validation/test
    split, but that split was NOT designed to prevent project leakage
    (the same project appears in multiple splits). We deliberately
    concatenate all three source splits and let SkyTrace's splitting.py
    produce a project-aware split downstream.

    Args:
        cfg: LoaderConfig; if None, loaded from configs/dataset.yaml
        sample_size: override cfg.sample_size for dev mode (applied per source split)
        streaming: if True, use streaming + manual batching (low memory)
    """
    cfg = cfg or LoaderConfig.from_yaml()
    if sample_size is not None:
        cfg.sample_size = sample_size

    os.makedirs(os.path.dirname(cfg.cache_dir), exist_ok=True)

    print(f"[loader] Loading DiverseVul from HuggingFace source='{cfg.source}', "
          f"revision={cfg.hf_revision}, sample_size={cfg.sample_size}, streaming={streaming}")

    # DiverseVul (bstee615/diversevul) ships 3 splits. Concatenate all of them
    # because we are doing our own project-aware split.
    source_splits = ["train", "validation", "test"]
    frames = []
    for sp in source_splits:
        print(f"[loader]   downloading source split='{sp}' ...")
        try:
            ds = load_dataset(
                cfg.source,
                name="default",
                revision=cfg.hf_revision,
                cache_dir=cfg.cache_dir,
                split=sp,
                streaming=streaming,
            )
        except Exception as e:
            print(f"[loader]   split='{sp}' load failed: {e}")
            continue

        if streaming:
            rows = []
            it = iter(ds)
            for i, row in enumerate(it):
                if cfg.sample_size is not None and i >= cfg.sample_size:
                    break
                rows.append(row)
            sub = pd.DataFrame(rows)
        else:
            sub = ds.to_pandas()
            if cfg.sample_size is not None and len(sub) > cfg.sample_size:
                sub = sub.head(cfg.sample_size).copy()

        sub["_source_split"] = sp
        frames.append(sub)
        print(f"[loader]   split='{sp}' rows={len(sub):,}")

    if not frames:
        raise RuntimeError("Could not load any source split from DiverseVul.")
    df = pd.concat(frames, ignore_index=True)
    print(f"[loader] Raw rows fetched (all source splits concatenated): {len(df):,}")
    print(f"[loader] Raw columns: {list(df.columns)}")

    df = _map_to_canonical(df, cfg)
    _dump_raw(df, cfg)
    return df


def _cwe_list_to_str(val) -> object:
    """Convert the raw `cwe` field into a canonical comma-separated string.

    bstee615/diversevul ships `cwe` as List[string] in the HF schema, but
    after datasets.to_pandas() the column actually comes back as a numpy
    array of objects, OR a Python list, OR (in some downstream round-trips)
    a string repr. We handle all three:
      (a) numpy ndarray / list / tuple  -> join items with ','
      (b) string repr "['CWE-416', 'CWE-787']"  -> ast.literal_eval then join
      (c) NaN / None / '[]'    -> NULL
    Empty container -> NULL, because that means 'no CWE recorded'.
    """
    import ast
    import numpy as np
    if val is None:
        return pd.NA
    if isinstance(val, float) and pd.isna(val):
        return pd.NA
    # numpy array
    if isinstance(val, np.ndarray):
        items = [str(x).strip() for x in val.tolist() if str(x).strip()]
        if not items:
            return pd.NA
        return ",".join(items)
    if isinstance(val, (list, tuple)):
        items = [str(x).strip() for x in val if str(x).strip()]
        if not items:
            return pd.NA
        return ",".join(items)
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "[]"):
        return pd.NA
    # String repr of a list, e.g. "['CWE-416', 'CWE-787']"
    if s.startswith("[") and s.endswith("]"):
        try:
            parsed = ast.literal_eval(s)
            if isinstance(parsed, (list, tuple)):
                items = [str(x).strip() for x in parsed if str(x).strip()]
                if not items:
                    return pd.NA
                return ",".join(items)
        except (ValueError, SyntaxError):
            pass
    return s


def _map_to_canonical(df: pd.DataFrame, cfg: LoaderConfig) -> pd.DataFrame:
    """Map raw DiverseVul columns to canonical SkyTrace schema."""
    cols = list(df.columns)

    mapping: Dict[str, Optional[str]] = {}
    for canonical, candidates in COLUMN_CANDIDATES.items():
        mapping[canonical] = _pick(cols, candidates)

    print("[loader] Column mapping resolved:")
    for k, v in mapping.items():
        print(f"    {k:<16} <- {v}")

    out = pd.DataFrame()

    # Code
    func_col = mapping["function_code"]
    out["function_code"] = df[func_col].astype("string") if func_col else pd.NA

    # Label — must exist
    label_col = mapping["label"]
    if label_col is None:
        raise ValueError("DiverseVul dataset has no recognisable label column. "
                         "Inspect raw columns and update COLUMN_CANDIDATES.")
    out["label"] = pd.to_numeric(df[label_col], errors="coerce").astype("Int64")

    # Identification
    out["project"] = df[mapping["project"]].astype("string") if mapping["project"] else pd.NA
    out["repository"] = out["project"]   # DiverseVul does not separate repo from project
    out["file_path"] = df[mapping["file_path"]].astype("string") if mapping["file_path"] else pd.NA

    # Security extras
    # CWE comes in as List[string]; normalise to comma-joined string.
    if mapping["cwe"]:
        out["cwe"] = df[mapping["cwe"]].apply(_cwe_list_to_str).astype("string")
    else:
        out["cwe"] = pd.NA
    out["cve"] = df[mapping["cve"]].astype("string") if mapping["cve"] else pd.NA

    # History
    out["commit_id"] = df[mapping["commit_id"]].astype("string") if mapping["commit_id"] else pd.NA
    # commit_date is NOT in the canonical DiverseVul release — left NULL,
    # to be derived later during repository mining.
    out["commit_date"] = pd.NA

    # Language — DiverseVul is C/C++ only.
    out["language"] = "c"

    # Function name — extract from source (best-effort)
    out["function_name"] = out["function_code"].apply(extract_function_name)

    # Sample ID — stable hash
    out["sample_id"] = [
        make_sample_id(c, p, cid)
        for c, p, cid in zip(out["function_code"], out["project"], out["commit_id"])
    ]

    # Also stash a function_code_hash for the audit phase — dropped before parquet.
    out["_function_hash"] = out["function_code"].apply(make_function_hash)

    # Keep raw extras as metadata (size, message, source split) — useful for audit
    # and for tracing provenance, but NOT part of canonical schema.
    if mapping["size"]:
        out["_raw_size"] = pd.to_numeric(df[mapping["size"]], errors="coerce")
    if mapping["commit_message"]:
        out["_raw_message"] = df[mapping["commit_message"]].astype("string")
    if mapping["hash"]:
        # bstee615 stores hash as float64 (a uint64 fingerprint cast to float).
        # Keep as float64 for audit; not part of canonical schema.
        out["_raw_hash"] = pd.to_numeric(df[mapping["hash"]], errors="coerce")
    if "_source_split" in df.columns:
        out["_source_split"] = df["_source_split"].astype("string")
    else:
        out["_source_split"] = pd.NA

    return out


def _dump_raw(df: pd.DataFrame, cfg: LoaderConfig) -> None:
    """Persist a copy of the mapped-but-not-cleaned dataframe for reproducibility."""
    os.makedirs(os.path.dirname(cfg.raw_dump_path), exist_ok=True)
    df.to_parquet(cfg.raw_dump_path, engine="pyarrow", compression="zstd", index=False)
    print(f"[loader] Wrote raw mapped parquet -> {cfg.raw_dump_path}")


if __name__ == "__main__":
    # Smoke test
    df = load_diversevul(sample_size=2000)
    print(df.head())
    print("cols:", list(df.columns))
    print("rows:", len(df))
