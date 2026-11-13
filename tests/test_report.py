"""Number formatting on the generated results pages."""

from mapaudit.report import _fmt


def test_tiny_p_values_stay_readable():
    assert _fmt(1.1e-14, "p") == "1.1e-14"
    assert _fmt(0.0123, "p") == "0.012"


def test_cells_cannot_break_the_table():
    assert _fmt("|bias|", "str") == "\\|bias\\|"


def test_no_negative_zero_and_readable_booleans():
    assert _fmt(-0.0001, "f3") == "0.000"
    assert _fmt(-0.01, "pp") == "+0.0"
    assert _fmt(True, "yesno") == "yes"
    assert _fmt(float("nan"), "f3") == "–"


def test_layout_check_catches_clipped_and_overlapping_text():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from mapaudit.plots import layout_problems

    fig = plt.figure(figsize=(4, 3))
    fig.text(0.1, 0.9, "A title that collides")
    fig.text(0.1, 0.9, "with this subtitle")
    fig.text(0.9, 0.5, "and this one runs off the right edge")
    problems = layout_problems(fig)
    plt.close(fig)
    assert any("overlaps" in p for p in problems)
    assert any("off the canvas" in p for p in problems)
