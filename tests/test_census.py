import numpy as np
import pandas as pd

from mapaudit.census import ID_COLUMNS, NUMERIC_COLUMNS, clean_iter, derive_indicators, read_iter
from mapaudit.synthetic import generate


def _row(ent, mun, loc, value="10", lat="19°00'00.000\" N", lon="99°00'00.000\" W"):
    row = dict.fromkeys(ID_COLUMNS, "x")
    row.update({"ENTIDAD": ent, "MUN": mun, "LOC": loc, "LATITUD": lat, "LONGITUD": lon, "ALTITUD": "2000"})
    row.update(dict.fromkeys(NUMERIC_COLUMNS, value))
    return row


def test_clean_iter_drops_aggregates_and_parses_codes():
    raw = pd.DataFrame(
        [
            _row("01", "001", "0001"),
            _row("01", "001", "0002", value="*"),  # tiny locality: suppressed values
            _row("01", "001", "0000"),  # municipal total
            _row("01", "001", "9998"),
            _row("01", "001", "9999"),
            _row("01", "000", "0000"),  # state total
            _row("00", "000", "0000"),  # national total
        ]
    )
    raw.loc[1, ["POBTOT", "VIVTOT"]] = "4"
    df = clean_iter(raw)
    assert list(df["cvegeo"]) == ["010010001", "010010002"]
    assert np.isnan(df.loc[1, "VIVPARH_CV"]) and df.loc[1, "POBTOT"] == 4
    assert df["lat"].iloc[0] == 19.0 and df["lon"].iloc[0] == -99.0


def test_derive_indicators_shares_are_bounded():
    raw = pd.DataFrame([_row("01", "001", "0001"), _row("01", "001", "0002", value="*")])
    raw.loc[1, ["POBTOT", "VIVTOT"]] = "4"
    df = derive_indicators(clean_iter(raw))
    shares = df[["no_elec", "has_fridge", "ind_hh_share", "illiterate"]].iloc[0]
    assert ((shares >= 0) & (shares <= 1)).all()
    assert bool(df["has_dwelling_data"].iloc[0]) and not bool(df["has_dwelling_data"].iloc[1])


def test_read_iter_from_zip(tmp_path, small_settings):
    generate(tmp_path, small_settings, seed=1)
    raw = read_iter(tmp_path / "iter_00_cpv2020_csv.zip")
    assert set(ID_COLUMNS + NUMERIC_COLUMNS) <= set(raw.columns)
    df = clean_iter(raw)
    assert df["cvegeo"].str.len().eq(9).all()
    assert df["lat"].between(14, 33).all()
