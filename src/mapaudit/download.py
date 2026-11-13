"""Download the public inputs into data/raw (skips files that already exist)."""

from __future__ import annotations

import sys
from pathlib import Path

import requests

from mapaudit.rwi import find_rwi_url


def _stream(url: str, dest: Path, timeout: int = 120) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))
        done = 0
        with open(tmp, "wb") as fh:
            for chunk in response.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
                done += len(chunk)
                if total:
                    sys.stdout.write(f"\r  {dest.name}: {done / total:6.1%}")
                    sys.stdout.flush()
    sys.stdout.write("\n")
    tmp.replace(dest)


def download_all(cfg: dict, raw_dir: Path) -> list[str]:
    """Fetch ITER and RWI. Returns human-readable messages, including manual-download hints."""
    sources = cfg["sources"]
    messages = []

    iter_src = sources["iter_2020"]
    dest = raw_dir / iter_src["filename"]
    if dest.exists():
        messages.append(f"ITER already present: {dest}")
    else:
        try:
            _stream(iter_src["url"], dest)
            messages.append(f"Downloaded ITER to {dest}")
        except requests.RequestException as err:
            messages.append(
                f"Could not download ITER ({err}). Download it manually from {iter_src['landing_page']} "
                f"and save it as {dest}"
            )

    rwi_src = sources["rwi"]
    dest = raw_dir / rwi_src["filename"]
    if dest.exists():
        messages.append(f"RWI already present: {dest}")
    else:
        try:
            url = find_rwi_url(rwi_src["hdx_api"], rwi_src["hdx_package"], rwi_src["country_iso3"])
            _stream(url, dest)
            messages.append(f"Downloaded RWI to {dest}")
        except (requests.RequestException, LookupError, KeyError) as err:
            messages.append(
                f"Could not download RWI ({err}). Check {rwi_src['landing_page']} for a Mexico file "
                f"and save it as {dest}. If Mexico is not covered, see docs/data_card.md (fallbacks)."
            )

    emb = sources["alphaearth"]
    messages.append(
        "Satellite features come from Google Earth Engine: run "
        f"`python scripts/gee_export_alphaearth.py --project YOUR_PROJECT`, then download the CSVs "
        f"from the Drive folder '{emb['drive_folder']}' into {raw_dir}."
    )
    return messages
