"""Satellite features exported from Google Earth Engine (AlphaEarth embeddings + VIIRS lights)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

EMBEDDING_COLUMNS = [f"A{i:02d}" for i in range(64)]
NIGHTLIGHT_COLUMN = "ntl_avg"


def read_embeddings(raw_dir: Path, file_glob: str) -> pd.DataFrame:
    """Concatenate the CSV parts exported by scripts/gee_export_alphaearth.py."""
    files = sorted(Path(raw_dir).glob(file_glob))
    if not files:
        raise FileNotFoundError(
            f"No files matching {file_glob!r} in {raw_dir}. Run scripts/gee_export_alphaearth.py "
            "and download the exported CSVs from Google Drive first."
        )
    parts = [pd.read_csv(f, dtype={"cvegeo": str}) for f in files]
    df = pd.concat(parts, ignore_index=True)
    df = df.drop(columns=[c for c in df.columns if c.startswith("system:") or c == ".geo"])
    df["cvegeo"] = df["cvegeo"].str.zfill(9)
    missing = [c for c in EMBEDDING_COLUMNS if c not in df.columns]
    if missing:
        raise KeyError(f"Embedding export is missing bands: {missing[:5]}...")
    df = df.drop_duplicates("cvegeo")
    if NIGHTLIGHT_COLUMN in df.columns:
        df["ntl_log"] = np.log1p(df[NIGHTLIGHT_COLUMN].clip(lower=0))
    return df


def embedding_norm_check(df: pd.DataFrame) -> float:
    """Median L2 norm of the embedding vectors.

    Single-pixel AlphaEarth embeddings are unit length; averages over a buffer are shorter, and
    the norm itself carries information about how homogeneous the surroundings are.
    """
    return float(np.median(np.linalg.norm(df[EMBEDDING_COLUMNS].to_numpy(), axis=1)))
