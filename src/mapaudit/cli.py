"""Command-line interface: ``mapaudit <step> [--demo]``."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time

from mapaudit import __version__, pipeline, report
from mapaudit.config import get_paths, load_config
from mapaudit.download import download_all


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def _timed(label: str, fn, *args):
    start = time.perf_counter()
    print(f"[mapaudit] {label} ...", flush=True)
    out = fn(*args)
    print(f"[mapaudit] {label} done in {time.perf_counter() - start:.1f}s", flush=True)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mapaudit", description="Who the Map Misses: audit pipeline")
    parser.add_argument("--version", action="version", version=f"mapaudit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in [
        ("download", "download ITER and RWI into data/raw"),
        ("build", "build the locality and tile tables"),
        ("audit", "audit the RWI against the census"),
        ("simulate", "train and score challenger models on simulated surveys"),
        ("robustness", "robustness checks from the pre-analysis plan"),
        ("report", "render figures and write the docs results page"),
        ("all", "build + audit + simulate + report"),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--demo", action="store_true", help="use synthetic data (results/demo)")
    demo = sub.add_parser("demo", help="generate synthetic data and run every step, including validation")
    demo.add_argument("--fresh", action="store_true", help="regenerate synthetic data first")
    sub.add_parser("validate", help="planted-bias validation on synthetic worlds")
    up = sub.add_parser("upload", help="stage new/changed files in upload/ for GitHub's web uploader")
    up.add_argument("--mark", action="store_true", help="record the current files as uploaded")
    gee = sub.add_parser("export-gee", help="start the Earth Engine export (see mapaudit/gee.py)")
    gee.add_argument("--project", required=True)
    gee.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    mode = "demo" if getattr(args, "demo", False) else "real"
    if args.command == "download":
        cfg, paths = load_config("real"), get_paths("real")
        for message in download_all(cfg, paths.raw):
            print(message)
    elif args.command == "build":
        _print(_timed("build", pipeline.build, mode))
    elif args.command == "audit":
        _print(_timed("audit", pipeline.audit, mode))
    elif args.command == "simulate":
        _print(_timed("simulate", pipeline.simulate, mode))
    elif args.command == "robustness":
        print(_timed("robustness", pipeline.robustness, mode).round(3).to_string(index=False))
    elif args.command == "report":
        _print(_timed("report", report.report, mode))
    elif args.command == "all":
        for label, fn in [
            ("build", pipeline.build),
            ("audit", pipeline.audit),
            ("robustness", pipeline.robustness),
            ("simulate", pipeline.simulate),
            ("report", report.report),
        ]:
            _timed(label, fn, mode)
    elif args.command == "upload":
        from mapaudit.upload import mark_uploaded, prepare_upload

        if args.mark:
            print(f"Recorded {mark_uploaded()} files as uploaded.")
        else:
            print(prepare_upload().describe())
    elif args.command == "export-gee":
        from mapaudit.gee import export_embeddings

        export_embeddings(args.project, dry_run=args.dry_run)
    elif args.command == "validate":
        print(_timed("validate", pipeline.validate).to_string(index=False))
    elif args.command == "demo":
        paths = get_paths("demo")
        if args.fresh and paths.data.exists():
            shutil.rmtree(paths.data)
        for label, fn in [
            ("build", pipeline.build),
            ("audit", pipeline.audit),
            ("robustness", pipeline.robustness),
            ("simulate", pipeline.simulate),
        ]:
            _timed(label, fn, "demo")
        _timed("validate", pipeline.validate)
        _print(_timed("report", report.report, "demo"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
