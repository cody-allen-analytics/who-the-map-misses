"""Geographic helpers: census coordinate parsing, Bing quadkeys, and great-circle distances."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

EARTH_RADIUS_KM = 6371.0088
_MAX_LAT = 85.05112878  # Web Mercator limit

# INEGI writes coordinates as degrees-minutes-seconds strings, e.g. 102°17'44.149" W.
_DMS = re.compile(
    r"^\s*(?P<deg>\d+(?:\.\d+)?)\D+(?P<min>\d+(?:\.\d+)?)\D+(?P<sec>\d+(?:\.\d+)?)\D*?(?P<hem>[NSEWnsew])\s*$"
)


def dms_to_decimal(value: object) -> float:
    """Convert one DMS string (or a decimal number) to signed decimal degrees."""
    if value is None:
        return np.nan
    if isinstance(value, int | float | np.number):
        return float(value)
    text = str(value).strip()
    if text in {"", "*", "N/D", "nan", "NaN"}:
        return np.nan
    try:
        return float(text)
    except ValueError:
        pass
    match = _DMS.match(text)
    if match is None:
        raise ValueError(f"Unrecognized coordinate format: {value!r}")
    decimal = float(match["deg"]) + float(match["min"]) / 60 + float(match["sec"]) / 3600
    return -decimal if match["hem"].upper() in {"W", "S"} else decimal


def parse_coordinates(values: pd.Series) -> np.ndarray:
    """Vectorized DMS parsing for a whole column."""
    parts = values.astype("string").str.extract(_DMS.pattern)
    decimal = (
        pd.to_numeric(parts["deg"], errors="coerce")
        + pd.to_numeric(parts["min"], errors="coerce") / 60
        + pd.to_numeric(parts["sec"], errors="coerce") / 3600
    )
    sign = np.where(parts["hem"].str.upper().isin(["W", "S"]), -1.0, 1.0)
    out = decimal.to_numpy(dtype=float) * sign
    # Fall back to plain numbers for rows that were already decimal degrees.
    plain = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    return np.where(np.isnan(out), plain, out)


def latlon_to_tile(lat: np.ndarray, lon: np.ndarray, zoom: int) -> tuple[np.ndarray, np.ndarray]:
    """Web Mercator tile indices (x, y) at ``zoom``."""
    lat = np.clip(np.asarray(lat, dtype=float), -_MAX_LAT, _MAX_LAT)
    lon = np.asarray(lon, dtype=float)
    n = 2**zoom
    x = np.floor((lon + 180.0) / 360.0 * n)
    lat_rad = np.radians(lat)
    y = np.floor((1.0 - np.log(np.tan(lat_rad) + 1.0 / np.cos(lat_rad)) / np.pi) / 2.0 * n)
    x = np.clip(x, 0, n - 1).astype(np.int64)
    y = np.clip(y, 0, n - 1).astype(np.int64)
    return x, y


def tile_to_quadkey(x: np.ndarray, y: np.ndarray, zoom: int) -> np.ndarray:
    """Bing Maps quadkeys for tile indices (one base-4 digit per zoom level)."""
    x = np.atleast_1d(np.asarray(x, dtype=np.int64))
    y = np.atleast_1d(np.asarray(y, dtype=np.int64))
    digits = np.zeros((x.size, zoom), dtype=np.int64)
    for level in range(zoom, 0, -1):
        mask = 1 << (level - 1)
        digits[:, zoom - level] = ((x & mask) != 0).astype(np.int64) + 2 * ((y & mask) != 0).astype(np.int64)
    # Build strings without a Python loop over digits.
    chars = digits.astype("U1")
    return np.array(["".join(row) for row in chars], dtype=object)


def latlon_to_quadkey(lat: np.ndarray, lon: np.ndarray, zoom: int) -> np.ndarray:
    x, y = latlon_to_tile(lat, lon, zoom)
    return tile_to_quadkey(x, y, zoom)


def quadkey_to_tile(quadkey: str) -> tuple[int, int, int]:
    x = y = 0
    zoom = len(quadkey)
    for i, char in enumerate(quadkey):
        mask = 1 << (zoom - i - 1)
        digit = int(char)
        if digit & 1:
            x |= mask
        if digit & 2:
            y |= mask
    return x, y, zoom


def tile_center(x: np.ndarray, y: np.ndarray, zoom: int) -> tuple[np.ndarray, np.ndarray]:
    """Latitude/longitude of tile centers."""
    n = 2**zoom
    lon = (np.asarray(x) + 0.5) / n * 360.0 - 180.0
    merc = np.pi * (1 - 2 * (np.asarray(y) + 0.5) / n)
    lat = np.degrees(np.arctan(np.sinh(merc)))
    return lat, lon


def haversine_km(lat1, lon1, lat2, lon2) -> np.ndarray:
    lat1, lon1, lat2, lon2 = (np.radians(np.asarray(v, dtype=float)) for v in (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def nearest_distance_km(
    src_lat: np.ndarray, src_lon: np.ndarray, dst_lat: np.ndarray, dst_lon: np.ndarray
) -> np.ndarray:
    """Distance from each source point to the nearest destination point (BallTree, haversine)."""
    if len(dst_lat) == 0:
        return np.full(len(src_lat), np.nan)
    tree = BallTree(np.radians(np.column_stack([dst_lat, dst_lon])), metric="haversine")
    dist, _ = tree.query(np.radians(np.column_stack([src_lat, src_lon])), k=1)
    return dist[:, 0] * EARTH_RADIUS_KM
