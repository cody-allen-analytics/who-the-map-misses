"""Synthetic stand-ins for every real input, written in the real file formats.

Why this exists:

1. CI can run the whole pipeline in about a minute without downloading gigabytes.
2. Validation: biases of known size are planted (a map that overstates wealth in Indigenous
   tiles, lower map coverage of Indigenous tiles, embeddings that see Indigenous places as
   wealthier than they are). The audit must find them when they are present and must not find
   them when they are absent. See ``mapaudit validate``.

Synthetic data is never presented as a finding about Mexico.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from mapaudit.census import ID_COLUMNS, NUMERIC_COLUMNS
from mapaudit.embeddings import EMBEDDING_COLUMNS
from mapaudit.geo import latlon_to_quadkey, latlon_to_tile, nearest_distance_km, tile_center

ITER_MEMBER = "iter_00_cpv2020/conjunto_de_datos/conjunto_de_datos_iter_00CSV20.csv"


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-x))


def _z(x: np.ndarray) -> np.ndarray:
    return (x - np.mean(x)) / (np.std(x) or 1.0)


def _dms(value: float, positive: str, negative: str) -> str:
    hem = positive if value >= 0 else negative
    value = abs(value)
    deg = int(value)
    minutes_full = (value - deg) * 60
    minutes = int(minutes_full)
    seconds = (minutes_full - minutes) * 60
    return f"{deg}°{minutes:02d}'{seconds:06.3f}\" {hem}"


def _localities(rng: np.random.Generator, s: dict) -> pd.DataFrame:
    n_states, n_mun = s["n_states"], s["n_municipalities"]
    st_lat = rng.uniform(16.5, 27.5, n_states)
    st_lon = rng.uniform(-108.0, -91.0, n_states)
    st_ind = np.full(n_states, 0.04)
    st_ind[: max(1, n_states // 3)] = 0.45
    st_effect = rng.normal(0, 0.35, n_states)
    st_alt = rng.uniform(200, 2200, n_states)

    m_state = np.arange(n_mun) % n_states
    m_lat = st_lat[m_state] + rng.normal(0, 0.8, n_mun)
    m_lon = st_lon[m_state] + rng.normal(0, 0.8, n_mun)
    m_ind = np.clip(st_ind[m_state] + rng.normal(0, 0.18, n_mun), 0, 0.95)
    m_effect = rng.normal(0, 0.3, n_mun)
    city_mun = {s_: int(np.flatnonzero(m_state == s_)[0]) for s_ in range(n_states)}

    frames = []
    for j in range(n_mun):
        k = 1 + rng.poisson(s["mean_localities_per_municipality"])
        pop = np.round(rng.lognormal(3.6, 1.5, k)).clip(1, 15000)
        pop[0] = np.round(rng.lognormal(8.0, 0.7))
        if j in city_mun.values():
            pop[0] = np.round(rng.uniform(8e4, 6e5))
        lat = m_lat[j] + rng.normal(0, 0.12, k)
        lon = m_lon[j] + rng.normal(0, 0.12, k)
        lat[0], lon[0] = m_lat[j], m_lon[j]
        ind = np.clip(m_ind[j] + rng.normal(0, 0.15, k) + 0.08 * (pop < 500), 0, 1)
        ind[0] = m_ind[j] * 0.6
        frames.append(
            pd.DataFrame(
                {
                    "state": m_state[j],
                    "mun": j,
                    "loc_idx": np.arange(k),
                    "POBTOT": pop,
                    "lat": lat,
                    "lon": lon,
                    "ind": ind,
                    "altitude": st_alt[m_state[j]] + rng.normal(0, 250, k),
                    "effect": st_effect[m_state[j]] + m_effect[j],
                }
            )
        )
    df = pd.concat(frames, ignore_index=True)
    cities = df[df["POBTOT"] >= 50000]
    df["dist_city"] = nearest_distance_km(df["lat"], df["lon"], cities["lat"], cities["lon"])
    noise = rng.normal(0, 0.45, len(df))
    df["w"] = (
        0.45 * _z(np.log(df["POBTOT"]))
        - 0.35 * _z(np.log1p(df["dist_city"]))
        + df["effect"]
        - 0.5 * df["ind"]
        + noise
    )
    return df


def _iter_table(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    w, ind, n = df["w"].to_numpy(), df["ind"].to_numpy(), len(df)

    def share(a, b, extra=0.0):
        return _sigmoid(a + b * w + extra + rng.normal(0, 0.3, n))

    shares = {
        "VPH_REFRI": share(1.0, 1.2), "VPH_LAVAD": share(0.0, 1.3), "VPH_AUTOM": share(-0.8, 1.1),
        "VPH_PC": share(-1.5, 1.4), "VPH_CEL": share(1.8, 1.0), "VPH_INTER": share(-1.0, 1.5),
        "VPH_TV": share(2.0, 0.9), "VPH_HMICRO": share(-0.7, 1.3),
        "VPH_S_ELEC": share(-3.5, -1.0, 0.6 * ind), "VPH_AGUAFV": share(-2.0, -1.1, 0.6 * ind),
        "VPH_NODREN": share(-1.5, -1.2, 0.6 * ind), "VPH_PISOTI": share(-2.5, -1.0, 0.6 * ind),
        "VPH_1CUART": share(-2.0, -0.8, 0.3 * ind),
    }  # fmt: skip
    pop = df["POBTOT"].to_numpy()
    dwellings = np.maximum(1, np.round(pop / 3.7 * rng.uniform(0.9, 1.1, n)))
    out = pd.DataFrame(
        {
            "ENTIDAD": (df["state"] + 1).map("{:02d}".format),
            "NOM_ENT": "Estado " + (df["state"] + 1).astype(str),
            "MUN": (df["mun"] + 1).map("{:03d}".format),
            "NOM_MUN": "Municipio " + (df["mun"] + 1).astype(str),
            "LOC": (df["loc_idx"] + 1).map("{:04d}".format),
            "NOM_LOC": "Localidad " + (df["loc_idx"] + 1).astype(str),
            "LONGITUD": [_dms(v, "E", "W") for v in df["lon"]],
            "LATITUD": [_dms(v, "N", "S") for v in df["lat"]],
            "ALTITUD": np.round(df["altitude"].clip(0)).astype(int).astype(str),
            "POBTOT": pop,
            "VIVTOT": np.round(dwellings * 1.1),
            "VIVPARH_CV": dwellings,
            "TVIVPARHAB": dwellings,
            "P_3YMAS": np.round(0.95 * pop),
            "P_15YMAS": np.round(0.72 * pop),
        }
    )
    out["P3YM_HLI"] = np.round(np.clip(0.85 * ind, 0, 1) * out["P_3YMAS"])
    out["PHOG_IND"] = np.round(ind * pop)
    illiterate = _sigmoid(-2.8 - 0.8 * w + 0.8 * ind + rng.normal(0, 0.3, n))
    no_basic = _sigmoid(0.0 - 0.9 * w + 0.5 * ind + rng.normal(0, 0.3, n))
    out["P15YM_AN"] = np.round(illiterate * out["P_15YMAS"])
    for col, frac in {"P15YM_SE": 0.15, "P15PRI_IN": 0.25, "P15PRI_CO": 0.3, "P15SEC_IN": 0.3}.items():
        out[col] = np.round(frac * no_basic * out["P_15YMAS"])
    out["PRO_OCUP_C"] = np.round(0.8 + 0.6 * _sigmoid(-w) + 0.2 * ind, 2)
    out["PSINDER"] = np.round(_sigmoid(-0.8 - 0.6 * w + 0.3 * ind) * pop)
    for col, p in shares.items():
        out[col] = np.round(p * dwellings)
    # ITER suppresses everything but a few totals when a locality has fewer than 3 dwellings.
    small = dwellings < 3
    keep_visible = {"POBTOT", "VIVTOT"}
    for col in NUMERIC_COLUMNS:
        values = out[col].astype("Int64").astype(str) if col != "PRO_OCUP_C" else out[col].astype(str)
        out[col] = values.where(~small | (col in keep_visible), "*")
    out.loc[rng.random(n) < 0.002, "ALTITUD"] = "N/D"
    return out[ID_COLUMNS + NUMERIC_COLUMNS]


def _aggregate_rows(table: pd.DataFrame) -> pd.DataFrame:
    """Municipal, state and national total rows, which the cleaner must drop."""
    numeric = table[NUMERIC_COLUMNS].apply(pd.to_numeric, errors="coerce")
    base = pd.concat([table[["ENTIDAD", "NOM_ENT", "MUN", "NOM_MUN"]], numeric], axis=1)
    rows = []
    for (ent, mun), part in base.groupby(["ENTIDAD", "MUN"]):
        totals = part[NUMERIC_COLUMNS].sum().round()
        for loc_code in ("0000", "9998", "9999"):
            row = {
                "ENTIDAD": ent,
                "MUN": mun,
                "LOC": loc_code,
                "NOM_ENT": part["NOM_ENT"].iloc[0],
                "NOM_MUN": part["NOM_MUN"].iloc[0],
                "NOM_LOC": "Total",
                "LONGITUD": "",
                "LATITUD": "",
                "ALTITUD": "",
            }
            row.update({c: str(int(totals[c])) if loc_code == "0000" else "0" for c in NUMERIC_COLUMNS})
            rows.append(row)
    for ent, part in base.groupby("ENTIDAD"):
        totals = part[NUMERIC_COLUMNS].sum().round()
        row = {
            "ENTIDAD": ent,
            "MUN": "000",
            "LOC": "0000",
            "NOM_ENT": part["NOM_ENT"].iloc[0],
            "NOM_MUN": "Total",
            "NOM_LOC": "Total",
            "LONGITUD": "",
            "LATITUD": "",
            "ALTITUD": "",
        }
        row.update({c: str(int(totals[c])) for c in NUMERIC_COLUMNS})
        rows.append(row)
    return pd.DataFrame(rows)[ID_COLUMNS + NUMERIC_COLUMNS]


def _rwi(df: pd.DataFrame, rng: np.random.Generator, s: dict) -> pd.DataFrame:
    zoom = 14
    tiles = df.assign(quadkey=latlon_to_quadkey(df["lat"].to_numpy(), df["lon"].to_numpy(), zoom))
    tiles["wx"] = tiles["w"] * tiles["POBTOT"]
    tiles["ix"] = tiles["ind"] * tiles["POBTOT"]
    agg = tiles.groupby("quadkey").agg(
        pop=("POBTOT", "sum"), wx=("wx", "sum"), ix=("ix", "sum"), lat=("lat", "first"), lon=("lon", "first")
    )
    w_tile, ind_tile = agg["wx"] / agg["pop"], agg["ix"] / agg["pop"]
    raw = 0.75 * _z(w_tile.to_numpy()) + s["rwi_indigenous_bias_sd"] * ind_tile.to_numpy()
    raw = raw + rng.normal(0, 0.45, len(agg))
    p_cover = _sigmoid(
        1.2 + 0.6 * np.log10(agg["pop"].to_numpy()) + s["rwi_coverage_indigenous_logit"] * ind_tile.to_numpy()
    )
    keep = rng.random(len(agg)) < p_cover
    x, y = latlon_to_tile(agg["lat"].to_numpy(), agg["lon"].to_numpy(), zoom)
    clat, clon = tile_center(x, y, zoom)
    out = pd.DataFrame(
        {
            "quadkey": agg.index,
            "latitude": np.round(clat, 6),
            "longitude": np.round(clon, 6),
            "rwi": np.round(_z(raw), 3),
            "error": np.round(rng.uniform(0.3, 0.6, len(agg)), 3),
        }
    )
    return out[keep].reset_index(drop=True)


def _embeddings(df: pd.DataFrame, cvegeo: pd.Series, rng: np.random.Generator, s: dict) -> pd.DataFrame:
    n = len(df)
    factors = np.column_stack(
        [
            df["w"] + s["embedding_indigenous_shift"] * df["ind"],
            _z(np.log(df["POBTOT"])),
            _z(np.log1p(df["dist_city"])),
            df["ind"],
            _z(df["altitude"]),
            rng.normal(size=(n, 3)),
        ]
    )
    mixing = rng.normal(0, 1, (factors.shape[1], 64))
    emb = factors @ mixing + rng.normal(0, 0.8, (n, 64))
    emb = emb / np.linalg.norm(emb, axis=1, keepdims=True) * rng.uniform(0.6, 1.0, (n, 1))
    out = pd.DataFrame(np.round(emb, 5), columns=EMBEDDING_COLUMNS)
    out.insert(0, "cvegeo", cvegeo.to_numpy())
    out.insert(0, "system:index", [f"{i:08x}" for i in range(n)])
    ntl = np.exp(0.9 * _z(np.log(df["POBTOT"])) + 0.4 * df["w"] - 0.4 * df["ind"] + rng.normal(0, 0.6, n)) - 1
    out["ntl_avg"] = np.round(np.clip(ntl, 0, None), 4)
    out[".geo"] = '{"type":"MultiPoint","coordinates":[]}'
    return out


def generate(raw_dir: Path, settings: dict, seed: int) -> dict:
    """Write the synthetic ITER zip, RWI CSV, embedding CSVs, and a record of planted effects."""
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    latent = _localities(rng, settings)
    table = _iter_table(latent, rng)
    full = pd.concat([table, _aggregate_rows(table)], ignore_index=True)
    national = {c: "" for c in ID_COLUMNS} | {"ENTIDAD": "00", "MUN": "000", "LOC": "0000"}
    national |= {c: "0" for c in NUMERIC_COLUMNS}
    full = pd.concat([full, pd.DataFrame([national])], ignore_index=True)
    full = full.sample(frac=1, random_state=seed).reset_index(drop=True)

    iter_path = raw_dir / "iter_00_cpv2020_csv.zip"
    buffer = io.StringIO()
    full.to_csv(buffer, index=False)
    with zipfile.ZipFile(iter_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(ITER_MEMBER, buffer.getvalue().encode("utf-8"))

    _rwi(latent, rng, settings).to_csv(raw_dir / "mex_relative_wealth_index.csv", index=False)

    cvegeo = table["ENTIDAD"] + table["MUN"] + table["LOC"]
    emb = _embeddings(latent, cvegeo, rng, settings)
    half = len(emb) // 2
    emb.iloc[:half].to_csv(raw_dir / "alphaearth_2020_part000.csv", index=False)
    emb.iloc[half:].to_csv(raw_dir / "alphaearth_2020_part001.csv", index=False)

    planted = {
        k: settings[k]
        for k in ("rwi_indigenous_bias_sd", "rwi_coverage_indigenous_logit", "embedding_indigenous_shift")
    }
    planted["localities"] = len(table)
    (raw_dir / "planted_effects.json").write_text(json.dumps(planted, indent=2))
    return planted
