"""Meta's Relative Wealth Index (RWI): download, read, join to census localities, aggregate to tiles.

RWI values are published per Bing tile (zoom 14, about 2.4 km at the equator) identified by a
quadkey. Every census locality is assigned to the tile that contains it, and census ground truth
is aggregated to the tile with population weights, so both sides are compared on the same unit.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import requests

from mapaudit.geo import latlon_to_quadkey, latlon_to_tile, tile_center, tile_to_quadkey
from mapaudit.labels import weighted_percentile_rank


def find_rwi_url(api_url: str, package: str, iso3: str, timeout: int = 60) -> str:
    """Look up the country file in the HDX package through the CKAN API."""
    response = requests.get(api_url, params={"id": package}, timeout=timeout)
    response.raise_for_status()
    resources = response.json()["result"]["resources"]
    key = iso3.lower()
    for res in resources:
        name = f"{res.get('name', '')} {res.get('url', '')}".lower()
        if f"{key}_relative_wealth_index" in name or f"/{key}_" in name:
            return res["url"]
    available = sorted({str(r.get("name")) for r in resources})
    raise LookupError(
        f"No RWI file for {iso3} in HDX package '{package}'. Available resources: {available[:20]}..."
    )


def quadkeys_from_tile_centres(lat: np.ndarray, lon: np.ndarray, zooms=(14, 13, 15, 16)) -> np.ndarray:
    """Recover quadkeys for an RWI file published without them (the Mexico file has only latitude,
    longitude, rwi and error). Its coordinates are tile centres, so the key is recomputed at the zoom
    whose tile centres they match; anything that is not a tile centre is refused rather than guessed."""
    lat, lon = np.asarray(lat, dtype=float), np.asarray(lon, dtype=float)
    for zoom in zooms:
        x, y = latlon_to_tile(lat, lon, zoom)
        clat, clon = tile_center(x, y, zoom)
        if np.all(np.maximum(np.abs(clat - lat), np.abs(clon - lon)) < 1e-4):
            return tile_to_quadkey(x, y, zoom)
    raise KeyError("RWI file has no quadkey column, and its coordinates are not tile centres at zoom 13-16")


def read_rwi(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"quadkey": str})
    df.columns = [c.strip().lower() for c in df.columns]
    if "quadkey" not in df.columns and {"latitude", "longitude"} <= set(df.columns):
        df["quadkey"] = quadkeys_from_tile_centres(df["latitude"], df["longitude"])
    required = {"quadkey", "latitude", "longitude", "rwi"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"RWI file is missing columns {sorted(missing)}")
    df["quadkey"] = df["quadkey"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    # Spreadsheet tools strip leading zeros, and every Mexican quadkey starts with 0. Pick the
    # zoom whose zero-padded quadkeys agree best with the published tile coordinates.
    longest = int(df["quadkey"].str.len().max())
    best_zoom, best_match = longest, -1.0
    for zoom in range(longest, longest + 3):
        padded = df["quadkey"].str.zfill(zoom).to_numpy()
        recomputed = latlon_to_quadkey(df["latitude"].to_numpy(), df["longitude"].to_numpy(), zoom)
        match = float(np.mean(padded == recomputed))
        if match > best_match:
            best_zoom, best_match = zoom, match
    df["quadkey"] = df["quadkey"].str.zfill(best_zoom)
    if "error" not in df.columns:
        df["error"] = np.nan
    return df[["quadkey", "latitude", "longitude", "rwi", "error"]]


def quadkey_consistency(rwi: pd.DataFrame) -> float:
    """Share of RWI rows whose own lat/lon falls inside the tile named by their quadkey."""
    zoom = len(rwi["quadkey"].iloc[0])
    recomputed = latlon_to_quadkey(rwi["latitude"].to_numpy(), rwi["longitude"].to_numpy(), zoom)
    return float(np.mean(recomputed == rwi["quadkey"].to_numpy()))


def attach_rwi(loc: pd.DataFrame, rwi: pd.DataFrame) -> pd.DataFrame:
    zoom = len(rwi["quadkey"].iloc[0])
    out = loc.copy()
    has_xy = out["lat"].notna() & out["lon"].notna()
    out["quadkey"] = pd.Series(pd.NA, index=out.index, dtype="object")
    out.loc[has_xy, "quadkey"] = latlon_to_quadkey(
        out.loc[has_xy, "lat"].to_numpy(), out.loc[has_xy, "lon"].to_numpy(), zoom
    )
    lookup = rwi.set_index("quadkey")[["rwi", "error"]].rename(columns={"error": "rwi_error"})
    out = out.join(lookup, on="quadkey")
    out["rwi_covered"] = out["rwi"].notna().astype(int)
    return out


def build_tiles(loc: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Aggregate in-scope localities to RWI tiles and compute the rank error RWI - census.

    ``rank_error`` is in percentile points: positive values mean the map ranks the tile as
    wealthier than the census does, i.e. it understates deprivation there. Tiles that contain an
    out-of-scope (urban) locality are dropped, because that locality's population cannot be
    placed correctly inside the tile grid.
    """
    out_of_scope_tiles = set(loc.loc[~loc["in_scope"] & loc["quadkey"].notna(), "quadkey"])
    covered = loc[
        loc["rwi"].notna()
        & loc["has_dwelling_data"]
        & loc["in_scope"]
        & ~loc["quadkey"].isin(out_of_scope_tiles)
    ].copy()
    w = covered["POBTOT"]
    covered["_w"] = w
    agg_cols = {
        "wealth_dhs_like": "wealth", "dep_infra": "dep_infra", "marg_index": "marg",
        "ind_share": "ind_share", "urban": "urban_share", "log_dist_city": "log_dist_city",
        "altitude_m": "altitude_m",
    }  # fmt: skip
    if "official_marg" in covered.columns:
        agg_cols["official_marg"] = "official_marg"
    for src in agg_cols:
        covered[f"_wx_{src}"] = covered[src] * w
        covered[f"_wn_{src}"] = w.where(covered[src].notna(), 0)
    grouped = covered.groupby("quadkey")
    tiles = grouped.agg(
        pop=("_w", "sum"),
        n_localities=("cvegeo", "size"),
        rwi=("rwi", "first"),
        lat=("lat", "mean"),
        lon=("lon", "mean"),
    )
    for src, dst in agg_cols.items():
        tiles[dst] = grouped[f"_wx_{src}"].sum() / grouped[f"_wn_{src}"].sum().replace(0, np.nan)
    # Assign each tile to the municipality and state of its most populous locality.
    top = covered.sort_values("POBTOT", ascending=False).drop_duplicates("quadkey").set_index("quadkey")
    tiles["cve_mun"] = top["cve_mun"]
    tiles["cve_ent"] = top["cve_ent"]
    tiles = tiles[tiles["pop"] > 0].copy()

    tiles["log_pop"] = np.log1p(tiles["pop"])
    tiles["altitude_km"] = tiles["altitude_m"] / 1000
    tiles["indigenous"] = (tiles["ind_share"] >= threshold).astype(int)
    tiles["rwi_pct"] = weighted_percentile_rank(tiles["rwi"], tiles["pop"])
    tiles["truth_pct"] = weighted_percentile_rank(tiles["wealth"], tiles["pop"])
    tiles["rank_error"] = 100 * (tiles["rwi_pct"] - tiles["truth_pct"])
    tiles["truth_decile"] = np.clip(np.floor(tiles["truth_pct"] * 10).astype(int) + 1, 1, 10)
    tiles["map_decile"] = np.clip(np.floor(tiles["rwi_pct"] * 10).astype(int) + 1, 1, 10)
    return tiles.reset_index()


def rwi_to_deprivation(loc: pd.DataFrame) -> pd.Series:
    """Quantile-map RWI onto the national distribution of ``dep_infra``.

    RWI is relative, so it can only rank places. To use it in a formula that needs a
    deprivation *rate*, assume the national distribution is known (e.g. from a survey) and give
    each locality the census deprivation value at its RWI rank. Uncovered localities receive the
    median of covered localities in their municipality, then the national median.
    """
    ref = loc[loc["has_dwelling_data"]]
    order = np.argsort(ref["dep_infra"].to_numpy())
    ref_vals = ref["dep_infra"].to_numpy()[order]
    ref_w = ref["POBTOT"].to_numpy()[order]
    cum = (np.cumsum(ref_w) - ref_w / 2) / ref_w.sum()

    covered = loc["rwi"].notna()
    poverty_pct = 1 - weighted_percentile_rank(loc.loc[covered, "rwi"], loc.loc[covered, "POBTOT"])
    est = pd.Series(np.nan, index=loc.index)
    est.loc[covered] = np.interp(poverty_pct, cum, ref_vals)
    mun_median = est.groupby(loc["cve_mun"]).transform("median")
    est = est.fillna(mun_median).fillna(np.nanmedian(est))
    return est
