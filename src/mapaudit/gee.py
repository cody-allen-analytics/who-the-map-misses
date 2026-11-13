"""Google Earth Engine export of AlphaEarth embeddings and VIIRS night lights per locality.

Use it from a notebook::

    import ee
    ee.Authenticate()                      # once per machine; opens a browser
    from mapaudit.gee import export_embeddings
    export_embeddings("my-gcp-project", dry_run=True)   # check one locality
    export_embeddings("my-gcp-project")                 # start the export tasks

or from a terminal: ``python scripts/gee_export_alphaearth.py --project my-gcp-project``.

Each chunk of localities becomes one export task that writes a CSV to the Google Drive folder named
in config/sources.yaml. Every locality gets the mean of each embedding band within a circular
buffer around its census coordinate; the buffer radius is a modelling choice recorded in the config.
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from mapaudit.config import get_paths, load_config
from mapaudit.embeddings import EMBEDDING_COLUMNS


def build_image(ee, year: int, emb_collection: str, ntl_collection: str, ntl_band: str):
    start, end = f"{year}-01-01", f"{year + 1}-01-01"
    embeddings = ee.ImageCollection(emb_collection).filterDate(start, end).mosaic()
    lights = (
        ee.ImageCollection(ntl_collection).filterDate(start, end).first().select(ntl_band).rename("ntl_avg")
    )
    return embeddings.select(EMBEDDING_COLUMNS).addBands(lights.unmask(0))


def to_feature_collection(ee, part: pd.DataFrame, buffer_m: float):
    points = [
        ee.Feature(ee.Geometry.Point([float(lon), float(lat)]), {"cvegeo": cvegeo})
        for cvegeo, lat, lon in part[["cvegeo", "lat", "lon"]].itertuples(index=False)
    ]
    # Buffer on the server so the request only carries point coordinates.
    return ee.FeatureCollection(points).map(lambda f: f.buffer(buffer_m))


def export_embeddings(
    project: str,
    year: int | None = None,
    buffer_m: float | None = None,
    scale_m: float | None = None,
    chunk: int = 5000,
    dry_run: bool = False,
) -> list[str]:
    """Start one Earth Engine export task per chunk of in-scope localities.

    With ``dry_run=True`` nothing is exported: the first locality's values are computed and
    returned, which checks authentication, the datasets and the locality table in one call.
    Returns the names of the tasks started (or a one-item list describing the dry-run result).
    """
    try:
        import ee
    except ImportError as err:
        raise ImportError("Install the Earth Engine API first: %pip install earthengine-api") from err

    cfg = load_config("real")
    src, ntl = cfg["sources"]["alphaearth"], cfg["sources"]["nightlights"]
    year = year or src["year"]
    buffer_m = buffer_m or src["buffer_m"]
    scale_m = scale_m or src["scale_m"]

    paths = get_paths("real")
    if not paths.localities.exists():
        raise FileNotFoundError("Build the locality table first (notebook 02, or `mapaudit build`).")
    loc = pd.read_parquet(paths.localities, columns=["cvegeo", "lat", "lon", "in_scope"])
    loc = loc[loc["in_scope"] & loc["lat"].notna()].reset_index(drop=True)
    n_tasks = -(-len(loc) // chunk)
    print(f"{len(loc):,} in-scope localities -> {n_tasks} export tasks")

    ee.Initialize(project=project)
    image = build_image(ee, year, src["ee_collection"], ntl["ee_collection"], ntl["band"])
    selectors = ["cvegeo", *EMBEDDING_COLUMNS, "ntl_avg"]
    started = []
    for i, start in enumerate(range(0, len(loc), chunk)):
        part = loc.iloc[start : start + chunk]
        stats = image.reduceRegions(
            collection=to_feature_collection(ee, part, buffer_m),
            reducer=ee.Reducer.mean(),
            scale=scale_m,
            tileScale=4,
        )
        if dry_run:
            first = stats.limit(1).getInfo()["features"][0]["properties"]
            print({k: first[k] for k in ("cvegeo", "A00", "A01", "ntl_avg") if k in first})
            return [f"dry run ok: {first.get('cvegeo')}"]
        name = f"alphaearth_{year}_part{i:03d}"
        task = ee.batch.Export.table.toDrive(
            collection=stats,
            description=name,
            folder=src["drive_folder"],
            fileNamePrefix=name,
            fileFormat="CSV",
            selectors=selectors,
        )
        task.start()
        started.append(name)
        print(f"started {name} ({len(part):,} localities)")
    print("Monitor the tasks at https://code.earthengine.google.com/tasks")
    return started


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export AlphaEarth embeddings per locality")
    parser.add_argument("--project", required=True, help="Google Cloud project registered for Earth Engine")
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--buffer", type=float, default=None, help="buffer radius in metres")
    parser.add_argument("--scale", type=float, default=None, help="reduction scale in metres")
    parser.add_argument("--chunk", type=int, default=5000, help="localities per export task")
    parser.add_argument("--dry-run", action="store_true", help="compute one locality, start nothing")
    args = parser.parse_args(argv)
    try:
        export_embeddings(args.project, args.year, args.buffer, args.scale, args.chunk, args.dry_run)
    except (ImportError, FileNotFoundError) as err:
        print(err, file=sys.stderr)
        return 1
    return 0
