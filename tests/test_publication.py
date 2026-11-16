"""Publication rules: aggregated tables only, and maps that show regions rather than communities."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from mapaudit import plots
from mapaudit.publication import identifier_columns


def test_identifier_columns_flags_locality_and_tile_keys(tmp_path):
    pd.DataFrame({"group": ["Indigenous"], "mean_error": [1.0]}).to_csv(tmp_path / "ok.csv", index=False)
    pd.DataFrame({"CVEGEO": ["010010001"], "rank_error": [3.0]}).to_csv(tmp_path / "leak.csv", index=False)
    (tmp_path / "sub").mkdir()
    pd.DataFrame({"quadkey": ["0231"], "pop": [10]}).to_csv(tmp_path / "sub" / "tiles.csv", index=False)
    assert identifier_columns(tmp_path) == ["leak.csv: CVEGEO", "sub/tiles.csv: quadkey"]


def _tiles(n_cluster: int) -> pd.DataFrame:
    """``n_cluster`` tiles at one spot in Oaxaca plus a single remote tile in Chihuahua."""
    rng = np.random.default_rng(0)
    cluster = pd.DataFrame(
        {
            "lon": -96.7,
            "lat": 17.06,
            "pop": rng.integers(10, 500, n_cluster).astype(float),
            "ind_share": rng.uniform(0, 1, n_cluster),
            "rank_error": rng.normal(0, 10, n_cluster),
        }
    )
    lone = pd.DataFrame(
        {"lon": [-106.1], "lat": [28.6], "pop": [80.0], "ind_share": [0.9], "rank_error": [25.0]}
    )
    return pd.concat([cluster, lone], ignore_index=True)


def _drawn(n_cluster: int):
    tiles = _tiles(n_cluster)
    fig = plots.fig_map(tiles, plots.THEMES["light"])
    hexes = [ax.collections[0] for ax in fig.axes[:2]]
    values = [np.asarray(h.get_array(), float) for h in hexes]
    plt.close(fig)
    return tiles, values


def test_map_hides_hexagons_with_too_few_tiles():
    _, values = _drawn(plots.MAP_MIN_TILES - 1)
    assert all(v.size == 0 for v in values)  # neither the small cluster nor the lone tile is drawn


def test_map_shows_population_weighted_means_of_dense_hexagons():
    tiles, (share, error) = _drawn(plots.MAP_MIN_TILES)
    cluster = tiles.iloc[: plots.MAP_MIN_TILES]
    assert share.size == 1 and error.size == 1  # the lone tile stays hidden
    assert np.isclose(share[0], np.average(cluster["ind_share"], weights=cluster["pop"]))
    assert np.isclose(error[0], np.average(cluster["rank_error"], weights=cluster["pop"]))
