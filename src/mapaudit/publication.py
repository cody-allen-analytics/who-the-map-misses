"""Publication rules: only aggregated results leave the analyst's computer.

The data card, the ethics page and section 10 of the pre-analysis plan promise that published
tables never identify a locality or a map tile. The pipeline's tables are aggregated by
construction (by group, decile, locality size or groups of municipalities); ``identifier_columns``
checks that this stays true. The end-to-end test runs it on every push, and the release check runs
it on the real-data tables before anything is shared.

Maps follow the same rule through hexagon aggregation (see ``MAP_HEX_KM`` in ``plots.py``).
"""

from __future__ import annotations

import csv
from pathlib import Path

# Column names (case-insensitive) that would tie a row to one locality or one map tile.
IDENTIFIER_COLUMNS = frozenset(
    {"cvegeo", "loc", "cve_loc", "nom_loc", "quadkey", "lat", "lon", "latitud", "longitud", "geometry"}
)


def identifier_columns(table_dir: Path) -> list[str]:
    """``file.csv: column`` for every CSV under ``table_dir`` with a locality- or tile-level key."""
    problems = []
    for path in sorted(Path(table_dir).rglob("*.csv")):
        with path.open(encoding="utf-8", newline="") as f:
            header = next(csv.reader(f), [])
        problems += [
            f"{path.relative_to(table_dir).as_posix()}: {col}"
            for col in header
            if col.strip().lower() in IDENTIFIER_COLUMNS
        ]
    return problems
