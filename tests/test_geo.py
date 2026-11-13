import numpy as np
import pandas as pd
import pytest

from mapaudit.geo import (
    dms_to_decimal,
    haversine_km,
    latlon_to_quadkey,
    latlon_to_tile,
    nearest_distance_km,
    parse_coordinates,
    quadkey_to_tile,
    tile_center,
    tile_to_quadkey,
)


def test_dms_strings_from_inegi():
    assert dms_to_decimal("102°17'44.149\" W") == pytest.approx(-(102 + 17 / 60 + 44.149 / 3600))
    assert dms_to_decimal("21°52'47.692\" N") == pytest.approx(21 + 52 / 60 + 47.692 / 3600)
    assert dms_to_decimal("-99.5") == -99.5
    assert np.isnan(dms_to_decimal("*"))
    with pytest.raises(ValueError):
        dms_to_decimal("not a coordinate")


def test_vectorized_parser_matches_scalar():
    values = pd.Series(["102°17'44.149\" W", "21°52'47.692\" N", "*", "-99.25"])
    parsed = parse_coordinates(values)
    expected = [dms_to_decimal(v) for v in values]
    np.testing.assert_allclose(parsed, expected, equal_nan=True)


def test_quadkey_matches_bing_documentation():
    # Bing Maps tile system docs: tile (3, 5) at level 3 has quadkey "213".
    assert tile_to_quadkey(np.array([3]), np.array([5]), 3)[0] == "213"
    assert quadkey_to_tile("213") == (3, 5, 3)


def test_quadkey_roundtrip_through_tile_center():
    lat, lon = np.array([19.43, 16.75, 25.67]), np.array([-99.13, -93.11, -100.31])
    x, y = latlon_to_tile(lat, lon, 14)
    clat, clon = tile_center(x, y, 14)
    np.testing.assert_array_equal(latlon_to_quadkey(clat, clon, 14), latlon_to_quadkey(lat, lon, 14))
    assert all(q.startswith("0") for q in latlon_to_quadkey(lat, lon, 14))  # Mexico is NW quadrant


def test_distances():
    # Mexico City to Guadalajara is about 461 km in a straight line.
    assert haversine_km(19.4326, -99.1332, 20.6597, -103.3496) == pytest.approx(461, abs=6)
    d = nearest_distance_km(
        np.array([19.0, 20.0]), np.array([-99.0, -99.0]), np.array([19.0]), np.array([-99.0])
    )
    assert d[0] == pytest.approx(0, abs=1e-6)
    assert d[1] == pytest.approx(111.2, abs=0.5)
