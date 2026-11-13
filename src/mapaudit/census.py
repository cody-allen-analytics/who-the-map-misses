"""Load INEGI's 2020 locality-level census file (ITER) and derive locality indicators.

Facts about the file this module relies on (see the ITER 2020 data dictionary):

* ENTIDAD (2), MUN (3) and LOC (4) are zero-padded codes; together they form the 9-digit CVEGEO.
* Aggregate rows: MUN == "000" (state/national totals) and LOC in {0000, 9998, 9999}
  (municipal totals and the pooled one- and two-dwelling localities).
* Localities with fewer than three dwellings show ``*`` for everything except
  POBTOT, VIVTOT and TVIVHAB. ``N/D`` marks unavailable values.
* LATITUD/LONGITUD are degrees-minutes-seconds strings.
* Dwelling indicators (VPH_*) refer to occupied private dwellings with recorded
  characteristics, whose total is VIVPARH_CV.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from mapaudit.geo import nearest_distance_km, parse_coordinates

ID_COLUMNS = ["ENTIDAD", "NOM_ENT", "MUN", "NOM_MUN", "LOC", "NOM_LOC", "LONGITUD", "LATITUD", "ALTITUD"]
NUMERIC_COLUMNS = [
    "POBTOT", "P_3YMAS", "P3YM_HLI", "PHOG_IND",
    "P_15YMAS", "P15YM_AN", "P15YM_SE", "P15PRI_IN", "P15PRI_CO", "P15SEC_IN",
    "VIVTOT", "VIVPARH_CV", "TVIVPARHAB", "PRO_OCUP_C",
    "VPH_S_ELEC", "VPH_AGUAFV", "VPH_NODREN", "VPH_PISOTI", "VPH_1CUART",
    "VPH_REFRI", "VPH_LAVAD", "VPH_AUTOM", "VPH_PC", "VPH_CEL", "VPH_INTER", "VPH_TV", "VPH_HMICRO",
    "PSINDER",
]  # fmt: skip
AGGREGATE_LOC_CODES = {"0000", "9998", "9999"}
MISSING_CODES = ["*", "N/D", ""]

# name of derived share -> (numerator column, denominator column)
DWELLING_SHARES = {
    "no_elec": "VPH_S_ELEC",
    "no_water": "VPH_AGUAFV",
    "no_drain": "VPH_NODREN",
    "dirt_floor": "VPH_PISOTI",
    "one_room": "VPH_1CUART",
    "has_fridge": "VPH_REFRI",
    "has_washer": "VPH_LAVAD",
    "has_car": "VPH_AUTOM",
    "has_pc": "VPH_PC",
    "has_cell": "VPH_CEL",
    "has_internet": "VPH_INTER",
    "has_tv": "VPH_TV",
    "has_micro": "VPH_HMICRO",
}


def _find_csv_member(archive: zipfile.ZipFile) -> str:
    names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
    preferred = [n for n in names if re.search(r"conjunto_de_datos_iter", n, re.IGNORECASE)]
    if preferred:
        return preferred[0]
    if names:
        return names[0]
    raise FileNotFoundError("No CSV file found inside the ITER zip archive.")


def read_iter(path: Path) -> pd.DataFrame:
    """Read the ITER CSV (or the zip INEGI distributes) with every column as text."""
    wanted = set(ID_COLUMNS) | set(NUMERIC_COLUMNS)
    path = Path(path)
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            if path.suffix.lower() == ".zip":
                with zipfile.ZipFile(path) as archive, archive.open(_find_csv_member(archive)) as fh:
                    df = pd.read_csv(
                        fh,
                        dtype=str,
                        encoding=encoding,
                        keep_default_na=False,
                        usecols=lambda c: c.strip().upper() in wanted,
                    )
            else:
                df = pd.read_csv(
                    path,
                    dtype=str,
                    encoding=encoding,
                    keep_default_na=False,
                    usecols=lambda c: c.strip().upper() in wanted,
                )
            df.columns = [c.strip().upper() for c in df.columns]
            missing = sorted(wanted - set(df.columns))
            if missing:
                raise KeyError(f"ITER file is missing expected columns: {missing}")
            return df
        except UnicodeDecodeError as err:  # try the next encoding
            last_error = err
    raise RuntimeError(f"Could not decode {path}") from last_error


def clean_iter(raw: pd.DataFrame) -> pd.DataFrame:
    """Drop aggregate rows, type the columns, and build locality keys and coordinates."""
    df = raw.copy()
    df["ENTIDAD"] = df["ENTIDAD"].str.strip().str.zfill(2)
    df["MUN"] = df["MUN"].str.strip().str.zfill(3)
    df["LOC"] = df["LOC"].str.strip().str.zfill(4)
    keep = (df["ENTIDAD"] != "00") & (df["MUN"] != "000") & ~df["LOC"].isin(AGGREGATE_LOC_CODES)
    df = df.loc[keep].copy()

    for col in NUMERIC_COLUMNS:
        # Always float: columns without suppressed values would otherwise come back as int64.
        df[col] = pd.to_numeric(df[col].replace(MISSING_CODES, np.nan), errors="coerce").astype(float)

    df["cvegeo"] = df["ENTIDAD"] + df["MUN"] + df["LOC"]
    df["cve_mun"] = df["ENTIDAD"] + df["MUN"]
    df["cve_ent"] = df["ENTIDAD"]
    df["lat"] = parse_coordinates(df["LATITUD"])
    df["lon"] = parse_coordinates(df["LONGITUD"])
    df["altitude_m"] = pd.to_numeric(df["ALTITUD"].replace(MISSING_CODES, np.nan), errors="coerce")
    if df["cvegeo"].duplicated().any():
        raise ValueError("Duplicate locality keys after cleaning; check the input file.")
    return df.reset_index(drop=True)


def _ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    out = num / den.where(den > 0)
    return out.clip(lower=0, upper=1)


def derive_indicators(df: pd.DataFrame, urban_min_population: int = 2500) -> pd.DataFrame:
    """Add shares (0-1) for Indigenous population, dwelling services, assets, and education."""
    out = df.copy()
    out["ind_hh_share"] = _ratio(out["PHOG_IND"], out["POBTOT"])
    out["ind_lang_share"] = _ratio(out["P3YM_HLI"], out["P_3YMAS"])
    for name, col in DWELLING_SHARES.items():
        out[name] = _ratio(out[col], out["VIVPARH_CV"])
    out["no_fridge"] = 1 - out["has_fridge"]
    out["illiterate"] = _ratio(out["P15YM_AN"], out["P_15YMAS"])
    no_basic = out[["P15YM_SE", "P15PRI_IN", "P15PRI_CO", "P15SEC_IN"]].sum(axis=1, min_count=4)
    out["no_basic_ed"] = _ratio(no_basic, out["P_15YMAS"])
    out["crowding"] = out["PRO_OCUP_C"]
    out["no_health_cov"] = _ratio(out["PSINDER"], out["POBTOT"])
    out["log_pop"] = np.log1p(out["POBTOT"])
    out["urban"] = (out["POBTOT"] >= urban_min_population).astype(int)
    needed = ["VIVPARH_CV", "VPH_REFRI", "VPH_S_ELEC", "VPH_AGUAFV", "VPH_NODREN", "VPH_PISOTI"]
    out["has_dwelling_data"] = out[needed].notna().all(axis=1) & (out["VIVPARH_CV"] > 0)
    return out


def add_remoteness(df: pd.DataFrame, city_min_population: int = 50000) -> pd.DataFrame:
    """Kilometres from each locality to the nearest locality with >= ``city_min_population``."""
    out = df.copy()
    cities = out[(out["POBTOT"] >= city_min_population) & out["lat"].notna()]
    has_xy = out["lat"].notna() & out["lon"].notna()
    dist = np.full(len(out), np.nan)
    dist[has_xy.to_numpy()] = nearest_distance_km(
        out.loc[has_xy, "lat"].to_numpy(),
        out.loc[has_xy, "lon"].to_numpy(),
        cities["lat"].to_numpy(),
        cities["lon"].to_numpy(),
    )
    out["dist_city_km"] = dist
    out["log_dist_city"] = np.log1p(out["dist_city_km"])
    return out


def add_indigenous_flags(df: pd.DataFrame, share_column: str, threshold: float) -> pd.DataFrame:
    out = df.copy()
    out["ind_share"] = out[share_column]
    out["indigenous"] = (out["ind_share"] >= threshold).astype("Int64")
    out.loc[out["ind_share"].isna(), "indigenous"] = pd.NA
    return out


def municipality_table(loc: pd.DataFrame, share_column: str, threshold: float) -> pd.DataFrame:
    """Population and Indigenous share per municipality (used for allocation summaries)."""
    weights = loc["POBTOT"].fillna(0)
    grouped = loc.assign(_w=weights, _wx=weights * loc[share_column].fillna(0)).groupby("cve_mun")
    mun = grouped.agg(pop=("_w", "sum"), ind_num=("_wx", "sum"), cve_ent=("cve_ent", "first"))
    mun["ind_share"] = mun["ind_num"] / mun["pop"].where(mun["pop"] > 0)
    mun["indigenous"] = (mun["ind_share"] >= threshold).astype(int)
    return mun.drop(columns="ind_num")
