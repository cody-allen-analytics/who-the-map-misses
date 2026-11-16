"""Figures, rendered in a light and a dark variant (``name.png`` and ``name-dark.png``).

Design rules (kept consistent across every figure):

* Emphasis, not rainbow: Indigenous = accent blue, non-Indigenous = muted gray, everywhere.
* One value axis per chart; hairline solid gridlines; thin marks; 2 px surface gaps/rings.
* Legends for two or more series, plus selective direct labels; text never wears a series color.
* Every figure has a table twin in results/<mode>/tables and on the docs results page.
* Nothing runs off the canvas or collides: subtitles wrap, and ``render`` warns about any text that
  leaves the canvas or overlaps other text (the end-to-end test fails on such a warning).
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MPath
from matplotlib.ticker import MaxNLocator

THEMES = {
    "light": {
        "surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781",
        "grid": "#e1e0d9", "axis": "#c3c2b7", "accent": "#2a78d6", "deemph": "#898781",
        "gain": "#2a78d6", "loss": "#e34948",
        "div": ["#184f95", "#6da7ec", "#f0efec", "#ef9a99", "#c23c3b"],
        "seq": ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"],
    },
    "dark": {
        "surface": "#1a1a19", "ink": "#f0efec", "ink2": "#c3c2b7", "muted": "#898781",
        "grid": "#2c2c2a", "axis": "#383835", "accent": "#3987e5", "deemph": "#898781",
        "gain": "#3987e5", "loss": "#e66767",
        "div": ["#9ec5f4", "#3987e5", "#383835", "#e66767", "#f3a5a5"],
        "seq": ["#104281", "#184f95", "#1c5cab", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4"],
    },
}  # fmt: skip
GROUPS = ["Indigenous", "Non-Indigenous"]
DPI = 200
PX = 72 / 100  # one CSS pixel in points at the 1x design size


def group_color(theme: dict, group: str) -> str:
    return theme["accent"] if group.startswith("Indigenous") else theme["deemph"]


def _style(theme: dict) -> None:
    plt.rcParams.update({
        "figure.facecolor": theme["surface"], "axes.facecolor": theme["surface"],
        "savefig.facecolor": theme["surface"], "text.color": theme["ink"],
        "axes.labelcolor": theme["ink2"], "xtick.color": theme["muted"], "ytick.color": theme["muted"],
        "xtick.labelcolor": theme["ink2"], "ytick.labelcolor": theme["ink2"],
        "axes.edgecolor": theme["axis"], "axes.linewidth": 1 * PX, "grid.color": theme["grid"],
        "grid.linewidth": 1 * PX, "grid.linestyle": "-", "font.family": "sans-serif",
        "font.sans-serif": ["Inter", "Helvetica Neue", "Arial", "Liberation Sans", "DejaVu Sans"],
        "font.size": 9.5, "axes.titlesize": 10, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
        "xtick.major.size": 0, "ytick.major.size": 0, "legend.frameon": False,
        "legend.fontsize": 8.5, "legend.labelcolor": theme["ink2"],
    })  # fmt: skip


def _frame(ax, theme: dict, value_axis: str = "y", baseline: bool = True) -> None:
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    if baseline:
        base = "bottom" if value_axis == "y" else "left"
        ax.spines[base].set_visible(True)
        ax.spines[base].set_color(theme["axis"])
    ax.grid(True, axis=value_axis)
    ax.set_axisbelow(True)


def _wrap_to_width(fig, text, right: float = 0.985) -> None:
    """Re-flow a text artist onto as many lines as it needs to end before ``right`` (figure fraction)."""
    fig.canvas.draw()
    limit = right * fig.bbox.width - text.get_window_extent().x0
    if text.get_window_extent().width <= limit:
        return
    lines, line = [], ""
    for word in text.get_text().split():
        trial = f"{line} {word}".strip()
        text.set_text(trial)
        if line and text.get_window_extent().width > limit:
            lines.append(line)
            line = word
        else:
            line = trial
    text.set_text("\n".join([*lines, line]))


def _titles(fig, title: str, subtitle: str, theme: dict) -> float:
    """Title and subtitle at fixed distances from the top edge, whatever the figure's height.

    The subtitle wraps instead of running off the canvas. Returns the subtitle's lower edge as a figure
    fraction, for figures that place a legend under it.
    """
    height = fig.get_figheight()
    fig.text(
        0.012,
        1 - 0.10 / height,
        title,
        ha="left",
        va="top",
        fontsize=12.5,
        fontweight="semibold",
        color=theme["ink"],
    )
    sub = fig.text(0.012, 1 - 0.40 / height, subtitle, ha="left", va="top", fontsize=9, color=theme["ink2"])
    _wrap_to_width(fig, sub)
    return sub.get_window_extent().y0 / fig.bbox.height


def _group_handles(theme: dict, labels: list[str], marker: str = "o") -> list[Line2D]:
    return [
        Line2D(
            [0],
            [0],
            marker=marker,
            color=group_color(theme, lab),
            lw=0 if marker == "s" else 2 * PX,
            markersize=7,
            markeredgecolor=theme["surface"],
            markeredgewidth=2 * PX,
            label=lab,
        )
        for lab in labels
    ]


def _legend(ax, theme: dict, labels: list[str], marker: str = "o") -> None:
    ax.legend(
        handles=_group_handles(theme, labels, marker),
        loc="lower left",
        bbox_to_anchor=(0, 1.0),
        ncol=len(labels),
        handletextpad=0.4,
        columnspacing=1.2,
        borderaxespad=0.2,
    )


def _dot_ci(ax, x, y, lo, hi, color, theme, horizontal=True) -> None:
    if horizontal:
        ax.plot([lo, hi], [y, y], color=color, lw=2 * PX, alpha=0.6, solid_capstyle="round", zorder=2)
        ax.plot(x, y, "o", color=color, ms=7.5, mec=theme["surface"], mew=2 * PX, zorder=3)
    else:
        ax.plot([x, x], [lo, hi], color=color, lw=2 * PX, alpha=0.6, solid_capstyle="round", zorder=2)
        ax.plot(x, y, "o", color=color, ms=7.5, mec=theme["surface"], mew=2 * PX, zorder=3)


def _per_inch(ax) -> tuple[float, float]:
    fig = ax.figure
    fig.canvas.draw()
    box = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
    return abs(x1 - x0) / box.width, abs(y1 - y0) / box.height


def _bar_path(x0, x1, y0, y1, rx, ry, end: str) -> MPath:
    """Rectangle with the two corners at the data ``end`` rounded (quadratic Bezier)."""
    rx = min(rx, (x1 - x0) / 2)
    ry = min(ry, (y1 - y0) / 2)
    L, C = MPath.LINETO, MPath.CURVE3
    if end == "top":
        pts = [
            (x0, y0),
            (x0, y1 - ry),
            (x0, y1),
            (x0 + rx, y1),
            (x1 - rx, y1),
            (x1, y1),
            (x1, y1 - ry),
            (x1, y0),
        ]
    elif end == "bottom":
        pts = [
            (x0, y1),
            (x0, y0 + ry),
            (x0, y0),
            (x0 + rx, y0),
            (x1 - rx, y0),
            (x1, y0),
            (x1, y0 + ry),
            (x1, y1),
        ]
    elif end == "right":
        pts = [
            (x0, y0),
            (x1 - rx, y0),
            (x1, y0),
            (x1, y0 + ry),
            (x1, y1 - ry),
            (x1, y1),
            (x1 - rx, y1),
            (x0, y1),
        ]
    else:  # left
        pts = [
            (x1, y0),
            (x0 + rx, y0),
            (x0, y0),
            (x0, y0 + ry),
            (x0, y1 - ry),
            (x0, y1),
            (x0 + rx, y1),
            (x1, y1),
        ]
    codes = [MPath.MOVETO, L, C, C, L, C, C, L]
    return MPath([*pts, pts[0]], [*codes, MPath.CLOSEPOLY])


def _bars(ax, centers, values, thickness, color, horizontal=True) -> None:
    """Bars from a zero baseline: 4 px rounded data end, square base, one path per bar."""
    xin, yin = _per_inch(ax)
    radius_in = 4 / 100  # 4 px at the 1x design size
    rx, ry = radius_in * xin, radius_in * yin
    for c, v in zip(centers, values, strict=True):
        if not np.isfinite(v) or v == 0:
            continue
        lo, hi = c - thickness / 2, c + thickness / 2
        if horizontal:
            path = _bar_path(min(0.0, v), max(0.0, v), lo, hi, rx, ry, "right" if v > 0 else "left")
        else:
            path = _bar_path(lo, hi, min(0.0, v), max(0.0, v), rx, ry, "top" if v > 0 else "bottom")
        ax.add_patch(PathPatch(path, facecolor=color, lw=0, zorder=2))


def _save(fig, out_dir: Path, name: str, theme_name: str) -> Path:
    suffix = "" if theme_name == "light" else "-dark"
    path = out_dir / f"{name}{suffix}.png"
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


# ---------------------------------------------------------------- figures


DECILE_VIEWS = {
    "truth_decile": {
        "title": "Does the map rank Indigenous places as wealthier than they are?",
        "subtitle": "Separation view: places equally wealthy in the census. Above zero = the map understates "
        "their deprivation. Bands: 95% municipality-cluster bootstrap.",
        "xlabel": "True wealth decile (census, population-weighted)",
        "ends": ("poorest", "wealthiest"),
    },
    "map_decile": {
        "title": "Among places the map ranks the same, are Indigenous ones poorer?",
        "subtitle": "Calibration view: places in the same decile of the map. A gap between the lines = places "
        "the map treats as equal are not equally poor. Bands: 95% municipality-cluster bootstrap.",
        "xlabel": "Map decile (the map's own ranking, population-weighted)",
        "ends": ("poorest", "wealthiest"),
    },
}


def fig_map_decile_errors(decile: pd.DataFrame, theme: dict) -> plt.Figure:
    return fig_decile_errors(decile, theme, by="map_decile")


def fig_decile_errors(decile: pd.DataFrame, theme: dict, by: str = "truth_decile") -> plt.Figure:
    view = DECILE_VIEWS[by]
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    fig.subplots_adjust(left=0.08, right=0.83, top=0.76, bottom=0.13)
    _frame(ax, theme)
    for g in GROUPS:
        d = decile[(decile["group"] == g) & (decile["n"] >= 5)].sort_values(by)
        if d.empty:
            continue
        col = group_color(theme, g)
        ax.fill_between(d[by], d["ci_low"], d["ci_high"], color=col, alpha=0.12, lw=0, zorder=1)
        ax.plot(d[by], d["mean_error"], color=col, lw=2 * PX, solid_joinstyle="round", zorder=2)
        ax.plot(
            d[by],
            d["mean_error"],
            "o",
            color=col,
            ms=6,
            mec=theme["surface"],
            mew=2 * PX,
            zorder=3,
        )
        last = d.iloc[-1]
        ax.annotate(
            f"{g} tiles",
            (last[by], last["mean_error"]),
            xytext=(10, 0),
            textcoords="offset points",
            va="center",
            fontsize=8.5,
            color=theme["ink2"],
        )
    ax.axhline(0, color=theme["axis"], lw=1.2 * PX, zorder=1)
    ax.set_xticks(range(1, 11))
    low, high = view["ends"]
    ax.set_xticklabels([f"1\n{low}", *map(str, range(2, 10)), f"10\n{high}"])
    ax.set_xlabel(view["xlabel"])
    ax.set_ylabel("Map rank − census rank (percentile points)")
    ax.set_xlim(0.6, 10.4)
    _legend(ax, theme, GROUPS)
    _titles(fig, view["title"], view["subtitle"], theme)
    return fig


def fig_coverage(coverage: pd.DataFrame, theme: dict) -> plt.Figure:
    data = coverage[coverage["size_class"] != "All"]
    sizes = [s for s in ["<100", "100-499", "500-2,499", "2,500+"] if s in set(data["size_class"])]
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    fig.subplots_adjust(left=0.08, right=0.97, top=0.74, bottom=0.15)
    _frame(ax, theme)
    ax.set_xlim(-0.6, len(sizes) - 0.4)
    ax.set_ylim(0, 1.05)
    xin, _ = _per_inch(ax)
    thickness = min(0.32, 0.24 * xin)  # cap at ~24 px at the 1x design size
    gap = 0.02 * xin  # 2 px surface gap between the paired bars
    for i, g in enumerate(GROUPS):
        vals = [
            data[(data["group"] == g) & (data["size_class"] == s)]["share_population_covered"].mean()
            for s in sizes
        ]
        offset = (i - 0.5) * (thickness + gap)
        centers = np.arange(len(sizes)) + offset
        _bars(ax, centers, vals, thickness, group_color(theme, g), horizontal=False)
        if g == "Indigenous":
            for cx, v in zip(centers, vals, strict=True):
                if np.isfinite(v):
                    ax.text(
                        cx, v + 0.02, f"{v:.0%}", ha="center", va="bottom", fontsize=8, color=theme["ink2"]
                    )
    ax.set_xticks(range(len(sizes)))
    ax.set_xticklabels([f"{s} people" for s in sizes])
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_ylabel("Population inside a map tile")
    ax.set_xlabel("Locality size")
    _legend(ax, theme, GROUPS, marker="s")
    _titles(
        fig,
        "Who is on the map at all?",
        "Share of each group's rural population that falls inside a Relative Wealth Index tile.",
        theme,
    )
    return fig


def fig_audit_specs(regs: pd.DataFrame, theme: dict) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8.4, 3.9))
    fig.subplots_adjust(left=0.2, right=0.97, top=0.76, bottom=0.16)
    _frame(ax, theme, value_axis="x", baseline=False)
    regs = regs.reset_index(drop=True)
    ys = np.arange(len(regs))[::-1]
    for y, (_, row) in zip(ys, regs.iterrows(), strict=True):
        _dot_ci(ax, row["coef"], y, row["ci_low"], row["ci_high"], theme["accent"], theme)
    ax.axvline(0, color=theme["axis"], lw=1.2 * PX)
    ax.set_yticks(ys)
    labels = {
        "1 none": "No controls",
        "2 + rurality": "+ settlement size",
        "3 + remoteness": "+ remoteness, altitude",
        "4 + true decile": "+ true wealth decile",
        "5 + state FE": "+ state fixed effects",
    }
    ax.set_yticklabels([labels.get(sp, sp) for sp in regs["spec"]])
    ax.set_ylim(-0.6, len(regs) - 0.4)
    ax.set_xlabel("Rank error for an all-Indigenous vs. a non-Indigenous tile (percentile points)")
    _titles(
        fig,
        "The gap survives controls for rurality, remoteness, true wealth, and state",
        "Coefficient on Indigenous population share, 95% CI clustered by municipality. Controls are cumulative.",
        theme,
    )
    return fig


def fig_label_choice(label: pd.DataFrame, theme: dict) -> plt.Figure:
    names = {
        "wealth_dhs_like": "Asset wealth (DHS-style)",
        "dep_infra": "Infrastructure deprivation",
        "marg_index": "Marginalization (CONAPO-style)",
    }
    order = list(names)
    fig, ax = plt.subplots(figsize=(8.4, 3.9))
    fig.subplots_adjust(left=0.27, right=0.95, top=0.74, bottom=0.15)
    _frame(ax, theme, value_axis="x")
    ax.set_xlim(0, 1.0)
    ax.set_ylim(-0.6, len(order) - 0.4)
    _, yin = _per_inch(ax)
    thickness, gap = min(0.3, 0.24 * yin), 0.02 * yin
    for i, g in enumerate(GROUPS):
        vals = [
            label[(label["label"] == lab) & (label["group"] == g)]["share_in_poorest"].mean() for lab in order
        ]
        centers = np.arange(len(order))[::-1] + (0.5 - i) * (thickness + gap)
        _bars(ax, centers, vals, thickness, group_color(theme, g), horizontal=True)
        for cy, v in zip(centers, vals, strict=True):
            if np.isfinite(v) and g == "Indigenous":
                ax.text(v + 0.012, cy, f"{v:.0%}", va="center", fontsize=8, color=theme["ink2"])
    ax.axvline(0.2, color=theme["muted"], lw=1 * PX)
    ax.set_yticks(np.arange(len(order))[::-1])
    ax.set_yticklabels([names[o] for o in order])
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_xlabel("Share of the group's population in the nation's poorest 20%")
    _legend(ax, theme, GROUPS, marker="s")
    _titles(
        fig,
        "Which poverty you measure changes who counts as poorest",
        "Same census, three definitions of poverty. Thin line: 20%, the share expected if poverty were evenly spread.",
        theme,
    )
    return fig


def fig_challengers(summary: pd.DataFrame, theme: dict) -> plt.Figure:
    if "weighting" in summary:
        summary = summary[summary["weighting"] == "people"]
    models = list(dict.fromkeys(summary["model"]))
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 4.0), sharey=True)
    fig.subplots_adjust(left=0.24, right=0.97, top=0.74, bottom=0.15, wspace=0.12)
    ys = np.arange(len(models))[::-1]
    for ax, metric, xlabel in [
        (axes[0], "bias", "Signed bias (predicted − true rate)"),
        (axes[1], "rmse", "RMSE"),
    ]:
        _frame(ax, theme, value_axis="x", baseline=False)
        for k, g in enumerate(GROUPS):
            d = summary[summary["group"] == g].set_index("model")
            for y, m in zip(ys, models, strict=True):
                if m in d.index:
                    r = d.loc[m]
                    _dot_ci(
                        ax,
                        r[f"{metric}_mean"],
                        y + (0.12 if k == 0 else -0.12),
                        r[f"{metric}_p025"],
                        r[f"{metric}_p975"],
                        group_color(theme, g),
                        theme,
                    )
        if metric == "bias":
            ax.axvline(0, color=theme["axis"], lw=1.2 * PX)
        ax.set_xlabel(xlabel)
        ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    axes[0].set_yticks(ys)
    axes[0].set_yticklabels(models)
    axes[0].set_ylim(-0.6, len(models) - 0.4)
    _legend(axes[0], theme, GROUPS)
    _titles(
        fig,
        "Challenger models trained on a simulated survey",
        "Infrastructure-deprivation rate in localities the survey did not visit. Whiskers: 95% range across replications.",
        theme,
    )
    return fig


def fig_conformal(summary: pd.DataFrame, model: str, alpha: float, theme: dict) -> plt.Figure:
    d = summary[(summary["model"] == model) & (summary["group"].isin(GROUPS))]
    methods = list(dict.fromkeys(d["method"]))
    frames = ["In survey frame", "Outside survey frame"]
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.9), sharey=True)
    fig.subplots_adjust(left=0.22, right=0.97, top=0.70, bottom=0.16, wspace=0.1)
    ys = np.arange(len(methods))[::-1]
    for ax, frame in zip(axes, frames, strict=True):
        _frame(ax, theme, value_axis="x", baseline=False)
        for k, g in enumerate(GROUPS):
            sub = d[(d["frame"] == frame) & (d["group"] == g)].set_index("method")
            for y, m in zip(ys, methods, strict=True):
                if m in sub.index:
                    r = sub.loc[m]
                    _dot_ci(
                        ax,
                        r["coverage_mean"],
                        y + (0.12 if k == 0 else -0.12),
                        r["coverage_p025"],
                        r["coverage_p975"],
                        group_color(theme, g),
                        theme,
                    )
        ax.axvline(1 - alpha, color=theme["muted"], lw=1 * PX)
        ax.set_title(frame, loc="left", color=theme["ink2"], fontsize=9.5)
        ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
        ax.set_xlabel(f"Coverage of {1 - alpha:.0%} intervals")
    lo = min(ax.get_xlim()[0] for ax in axes)
    hi = max(max(ax.get_xlim()[1] for ax in axes), 1 - alpha + 0.02)
    for ax in axes:
        ax.set_xlim(lo, hi)
    axes[0].set_yticks(ys)
    axes[0].set_yticklabels(methods)
    axes[0].set_ylim(-0.6, len(methods) - 0.4)
    _legend(axes[0], theme, GROUPS)
    axes[0].get_legend().set_bbox_to_anchor((0, 1.1))
    _titles(
        fig,
        "Honest uncertainty needs group-conditional calibration and the right sample",
        f"{model}. Thin line: target coverage. 'Survey frame' = localities large enough to be surveyed.",
        theme,
    )
    return fig


def fig_allocation(by_share: pd.DataFrame, by_model: pd.DataFrame, theme: dict) -> plt.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.1), gridspec_kw={"width_ratios": [1.1, 1]})
    fig.subplots_adjust(left=0.08, right=0.97, top=0.74, bottom=0.2, wspace=0.55)
    ax = axes[0]
    _frame(ax, theme)
    vals = by_share["net_shift_pct"].to_numpy()
    lim = max(0.05, np.nanmax(np.abs(vals)) * 1.25)
    ax.set_xlim(-0.6, len(vals) - 0.4)
    ax.set_ylim(-lim, lim)
    colors = [theme["loss"] if v < 0 else theme["gain"] for v in vals]
    for i, (v, c) in enumerate(zip(vals, colors, strict=True)):
        _bars(ax, [i], [v], 0.42, c, horizontal=False)
        ax.text(
            i,
            v + (0.02 * lim if v >= 0 else -0.02 * lim),
            f"{v:+.0%}".replace("-", "\u2212"),
            ha="center",
            va="bottom" if v >= 0 else "top",
            fontsize=8,
            color=theme["ink2"],
        )
    ax.axhline(0, color=theme["axis"], lw=1.2 * PX)
    ax.set_xticks(range(len(vals)))
    ax.set_xticklabels(by_share["ind_bin"].astype(str))
    ax.set_xlabel("Municipality's Indigenous population share")
    ax.set_ylabel("Change vs. census-based allocation")
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_title("Relative Wealth Index", loc="left", color=theme["ink2"], fontsize=9.5)

    ax = axes[1]
    _frame(ax, theme, value_axis="x", baseline=False)
    rows = by_model.reset_index(drop=True)
    ys = np.arange(len(rows))[::-1]
    for y, (_, r) in zip(ys, rows.iterrows(), strict=True):
        _dot_ci(ax, r["mean"], y, r["low"], r["high"], theme["accent"], theme)
    ax.axvline(0, color=theme["axis"], lw=1.2 * PX)
    ax.set_yticks(ys)
    ax.set_yticklabels(rows["model"])
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_xlabel("Change for Indigenous-majority municipalities")
    ax.set_title("All maps", loc="left", color=theme["ink2"], fontsize=9.5)
    _titles(
        fig,
        "What the errors cost: a FAIS-style infrastructure budget",
        "Budget split by estimated number of deprived people, using each map instead of the census.",
        theme,
    )
    return fig


# Publication rule for maps (pre-analysis plan §10, ethics page): published maps show regions, not
# communities. Tiles are averaged into hexagons about MAP_HEX_KM across, and a hexagon holding fewer
# than MAP_MIN_TILES map tiles is not drawn, so no single locality can be read off the figure.
MAP_HEX_KM = 40
MAP_MIN_TILES = 5


def _hex_grid(lon: np.ndarray, lat: np.ndarray) -> tuple[tuple[int, int], tuple[float, ...]]:
    """Hexbin grid size and extent for hexagons about MAP_HEX_KM across that look regular on a map
    whose latitude axis is stretched by 1 / cos(mean latitude)."""
    coslat = float(np.cos(np.radians(np.nanmean(lat))))
    xmin, xmax, ymin, ymax = np.nanmin(lon), np.nanmax(lon), np.nanmin(lat), np.nanmax(lat)
    xr, yr = max(xmax - xmin, 1e-6), max(ymax - ymin, 1e-6)
    nx = max(1, int(np.ceil(xr / (MAP_HEX_KM / (111.32 * coslat)))))
    # matplotlib's hexagons are regular when row spacing = sqrt(3) x column spacing on screen.
    ny = max(1, round(float(yr * nx / (np.sqrt(3) * xr * coslat))))
    return (nx, ny), (xmin, xmin + xr, ymin, ymin + yr)


def _hex_means(ax, lon, lat, values, weights, cmap, gridsize, extent):
    """Population-weighted mean of ``values`` per hexagon; hexagons with too few tiles stay empty."""

    def weighted_mean(idx) -> float:
        idx = np.asarray(idx, dtype=int)
        w = weights[idx]
        return float(np.average(values[idx], weights=w)) if w.sum() > 0 else np.nan

    return ax.hexbin(
        lon,
        lat,
        C=np.arange(len(lon)),
        reduce_C_function=weighted_mean,
        gridsize=gridsize,
        extent=extent,
        mincnt=MAP_MIN_TILES,
        cmap=cmap,
        linewidths=0,
    )


def fig_map(tiles: pd.DataFrame, theme: dict) -> plt.Figure:
    """Regional pattern of Indigenous share and rank error, aggregated to hexagons (see MAP_HEX_KM)."""
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.6))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.84, bottom=0.12, wspace=0.08)
    seq = LinearSegmentedColormap.from_list("seq", theme["seq"])
    div = LinearSegmentedColormap.from_list("div", theme["div"])
    lon, lat = tiles["lon"].to_numpy(float), tiles["lat"].to_numpy(float)
    pop = tiles["pop"].to_numpy(float)
    gridsize, extent = _hex_grid(lon, lat)
    panels = [
        (axes[0], tiles["ind_share"].to_numpy(float), seq, False, "Indigenous population share"),
        (axes[1], tiles["rank_error"].to_numpy(float), div, True, "Map rank − census rank (pp)"),
    ]
    for ax, values, cmap, symmetric, label in panels:
        ok = np.isfinite(lon) & np.isfinite(lat) & np.isfinite(values) & (pop > 0)
        hexes = _hex_means(ax, lon[ok], lat[ok], values[ok], pop[ok], cmap, gridsize, extent)
        if symmetric:
            means = np.abs(np.asarray(hexes.get_array(), float))
            lim = float(np.nanpercentile(means, 95)) if means.size else 0.0
            hexes.set_clim(-(lim or 1.0), lim or 1.0)
        else:
            hexes.set_clim(0, 1)
        ax.set_xlim(extent[0], extent[1])
        ax.set_ylim(extent[2], extent[3])
        ax.set_aspect(1 / np.cos(np.radians(np.nanmean(lat))))
        ax.axis("off")
        cbar = fig.colorbar(hexes, ax=ax, orientation="horizontal", fraction=0.04, pad=0.02, shrink=0.6)
        cbar.outline.set_visible(False)
        cbar.ax.tick_params(labelsize=7.5, colors=theme["muted"], labelcolor=theme["ink2"])
        cbar.set_label(label, fontsize=8, color=theme["ink2"])
    _titles(
        fig,
        "Where the map and the census disagree",
        f"{MAP_HEX_KM} km hexagons, each the population-weighted mean of {MAP_MIN_TILES}+ map tiles. Red = map ranks the area wealthier than the census.",
        theme,
    )
    return fig


def fig_challenger_deciles(summary: pd.DataFrame, theme: dict) -> plt.Figure:
    models = list(dict.fromkeys(summary["model"]))
    n = len(models)
    cols = 2
    rows_n = -(-n // cols)
    fig, axes = plt.subplots(
        rows_n, cols, figsize=(8.8, 2.6 * rows_n + 1.2), sharex=True, sharey=True, squeeze=False
    )
    fig.subplots_adjust(
        left=0.09, right=0.98, top=1 - 1.15 / (2.6 * rows_n + 1.2), bottom=0.1, hspace=0.42, wspace=0.08
    )
    for k, ax in enumerate(axes.flat):
        if k >= n:
            ax.set_visible(False)
            continue
        _frame(ax, theme)
        d_model = summary[summary["model"] == models[k]]
        for g in GROUPS:
            d = d_model[d_model["group"] == g].sort_values("decile")
            if d.empty:
                continue
            col = group_color(theme, g)
            ax.fill_between(
                d["decile"], 100 * d["bias_p025"], 100 * d["bias_p975"], color=col, alpha=0.12, lw=0
            )
            ax.plot(d["decile"], 100 * d["bias_mean"], color=col, lw=2 * PX)
            ax.plot(
                d["decile"], 100 * d["bias_mean"], "o", color=col, ms=4.5, mec=theme["surface"], mew=1.5 * PX
            )
        ax.axhline(0, color=theme["axis"], lw=1.2 * PX)
        ax.set_title(models[k], loc="left", color=theme["ink2"], fontsize=9.5)
        ax.set_xticks(range(1, 11))
        ax.set_xticklabels(["1\nleast", *map(str, range(2, 10)), "10\nmost"])
    for ax in axes[-1]:
        ax.set_xlabel("True deprivation decile")
    for ax in axes[:, 0]:
        ax.set_ylabel("Mean error (pp)")
    sub_bottom = _titles(
        fig,
        "Where each model's errors fall",
        "Mean error in localities the survey never visited, by true deprivation decile. Below zero on the "
        "right = the model under-predicts deprivation where it is highest. Bands: 95% range across "
        "replications.",
        theme,
    )
    height = fig.get_figheight()
    fig.legend(
        handles=_group_handles(theme, GROUPS),
        loc="upper left",
        bbox_to_anchor=(0.004, sub_bottom - 0.05 / height),
        ncol=len(GROUPS),
        handletextpad=0.4,
        columnspacing=1.2,
    )
    fig.subplots_adjust(top=sub_bottom - 0.68 / height)
    return fig


def fig_validation(table: pd.DataFrame, theme: dict) -> plt.Figure:
    has_gaps = "separation_gap_pp" in table
    fig, axes = plt.subplots(1, 3 if has_gaps else 2, figsize=(9.6 if has_gaps else 8.8, 3.3), sharey=True)
    fig.subplots_adjust(left=0.16, right=0.98, top=0.64, bottom=0.2, wspace=0.14)
    ys = np.arange(len(table))[::-1]
    specs = [("rank_error", "Rank-error coefficient (pp)"), ("coverage", "Coverage coefficient")]
    if has_gaps:
        ax = axes[2]
        _frame(ax, theme, value_axis="x", baseline=False)
        views = [("separation_gap_pp", "Equally poor in census", theme["accent"], 0.12),
                 ("calibration_gap_pp", "Ranked equally by map", theme["deemph"], -0.12)]  # fmt: skip
        for col, _, color, offset in views:
            for y, (_, r) in zip(ys, table.iterrows(), strict=True):
                ax.plot(r[col], y + offset, "o", color=color, ms=7.5, mec=theme["surface"], mew=2 * PX)
        ax.axvline(0, color=theme["axis"], lw=1.2 * PX)
        values = table[[c for c, *_ in views]].to_numpy(dtype=float)
        pad = 0.15 * max(np.nanmax(np.abs(values)), 1.0)
        ax.set_xlim(min(np.nanmin(values), 0) - pad, max(np.nanmax(values), 0) + pad)
        ax.set_xlabel("Gap within deciles (pp)")
        handles = [
            Line2D([0], [0], marker="o", lw=0, color=c, markersize=7, label=lab) for _, lab, c, _ in views
        ]
        ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=1, handletextpad=0.3)
    for ax, (key, xlabel) in zip(axes[:2], specs, strict=True):
        _frame(ax, theme, value_axis="x", baseline=False)
        for y, (_, r) in zip(ys, table.iterrows(), strict=True):
            _dot_ci(ax, r[f"{key}_coef"], y, r[f"{key}_ci_low"], r[f"{key}_ci_high"], theme["accent"], theme)
        ax.axvline(0, color=theme["axis"], lw=1.2 * PX)
        ax.set_xlabel(xlabel)
    for ax in axes:
        ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
    axes[0].set_yticks(ys)
    axes[0].set_yticklabels(table["world"])
    axes[0].set_ylim(-0.6, len(table) - 0.4)
    _titles(
        fig,
        "Validation: the audit finds planted bias and stays quiet without it",
        "Synthetic worlds with and without a planted Indigenous bias. Right: places the map ranks equally "
        "show a gap even without bias.",
        theme,
    )
    return fig


class FigureLayoutWarning(UserWarning):
    """A figure has text outside its canvas or text drawn on top of other text."""


def layout_problems(fig) -> list[str]:
    """Content that runs off the canvas, and titles, labels or legend entries that overlap."""
    fig.canvas.draw()
    problems = []
    tight, canvas = fig.get_tightbbox(), fig.bbox_inches
    if (
        tight.x0 < canvas.x0 - 0.01
        or tight.y0 < canvas.y0 - 0.01
        or tight.x1 > canvas.x1 + 0.01
        or tight.y1 > canvas.y1 + 0.01
    ):
        problems.append("content runs off the canvas")
    axes = [ax for ax in fig.axes if ax.get_visible()]
    legends = [*fig.legends, *(ax.get_legend() for ax in axes if ax.get_legend() is not None)]
    texts = [
        *(t for t in fig.texts if t.get_text()),
        *(t for leg in legends for t in leg.get_texts()),
        *(t for ax in axes for t in (ax.title, ax.xaxis.label, ax.yaxis.label) if t.get_text()),
    ]
    boxes = [(t.get_text(), t.get_window_extent()) for t in texts]
    for i, (a_text, a) in enumerate(boxes):
        for b_text, b in boxes[i + 1 :]:
            if min(a.x1, b.x1) - max(a.x0, b.x0) > 2 and min(a.y1, b.y1) - max(a.y0, b.y0) > 2:
                problems.append(f"{a_text[:30]!r} overlaps {b_text[:30]!r}")
    return problems


def render(name: str, builder, out_dir: Path, *args) -> list[Path]:
    """Render a figure in both themes, warning about layout problems."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for theme_name, theme in THEMES.items():
        _style(theme)
        fig = builder(*args, theme)
        for problem in layout_problems(fig):
            warnings.warn(f"{name} ({theme_name}): {problem}", FigureLayoutWarning, stacklevel=2)
        paths.append(_save(fig, out_dir, name, theme_name))
    return paths
