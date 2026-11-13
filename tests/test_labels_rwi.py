import numpy as np
import pandas as pd
import pytest

from mapaudit.geo import latlon_to_tile, tile_center, tile_to_quadkey
from mapaudit.labels import first_component, weighted_percentile_rank
from mapaudit.rwi import quadkey_consistency, read_rwi


def test_weighted_percentile_rank_midpoints_ties_and_nans():
    ranks = weighted_percentile_rank(np.array([3.0, 1.0, 2.0, 4.0]), np.ones(4))
    np.testing.assert_allclose(ranks, [0.625, 0.125, 0.375, 0.875])
    tied = weighted_percentile_rank(np.array([1.0, 1.0, 2.0]), np.ones(3))
    assert tied[0] == tied[1]
    with_nan = weighted_percentile_rank(np.array([1.0, np.nan, 2.0]), np.ones(3))
    assert np.isnan(with_nan[1])
    heavy = weighted_percentile_rank(np.array([1.0, 2.0]), np.array([3.0, 1.0]))
    np.testing.assert_allclose(heavy, [0.375, 0.875])


def test_first_component_is_signed_by_reference():
    rng = np.random.default_rng(0)
    latent = rng.normal(size=500)
    df = pd.DataFrame({"a": latent + rng.normal(0, 0.3, 500), "b": -latent + rng.normal(0, 0.3, 500)})
    scores, loadings = first_component(df, ["a", "b"], reference="a")
    assert loadings["a"] > 0 > loadings["b"]
    assert np.corrcoef(scores, latent)[0, 1] > 0.9


def test_read_rwi_restores_leading_zeros(tmp_path):
    lat, lon = np.array([17.05, 20.67, 16.75]), np.array([-96.72, -103.35, -93.11])
    x, y = latlon_to_tile(lat, lon, 14)
    clat, clon = tile_center(x, y, 14)
    qk = tile_to_quadkey(x, y, 14)
    stripped = [str(int(q)) for q in qk]  # what a spreadsheet does to "0231..."
    path = tmp_path / "rwi.csv"
    pd.DataFrame({"quadkey": stripped, "latitude": clat, "longitude": clon, "rwi": [0.1, -0.2, 0.3]}).to_csv(
        path, index=False
    )
    rwi = read_rwi(path)
    assert list(rwi["quadkey"]) == list(qk)
    assert quadkey_consistency(rwi) == pytest.approx(1.0)
