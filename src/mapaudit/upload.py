"""Prepare uploads for GitHub's web interface, for working without git on your computer.

GitHub's "Add file -> Upload files" page accepts up to 100 files (25 MiB each) per commit and keeps
folder structure when you drag a folder, but it refuses hidden folders such as ``.github``.

``prepare_upload()`` compares the project with a local manifest of what you uploaded last time and
copies only new or changed files into ``upload/``, mirroring the repository layout, so you can drag
its folders onto the upload page. Files that must not go to GitHub (raw data, demo outputs, caches)
are skipped, mirroring .gitignore. After uploading, ``mark_uploaded()`` records the new state.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from mapaudit.config import repo_root

MANIFEST = ".upload_manifest.json"
OUT_DIR = "upload"
GITHUB_FILE_LIMIT = 100
GITHUB_SIZE_LIMIT = 25 * 1024 * 1024

EXCLUDE = [
    ".git/*", "data/*", "results/demo/*", "site/*", f"{OUT_DIR}/*", MANIFEST,
    "*__pycache__*", "*.pyc", "*.egg-info*", "*.ipynb_checkpoints*", ".venv/*", "venv/*",
    ".pytest_cache/*", ".ruff_cache/*", ".coverage", "htmlcov/*", "build/*", "dist/*",
    "*.DS_Store", "*Thumbs.db", ".idea/*", ".vscode/*", "*.ipynb_checkpoints/*", ".virtual_documents/*",
]  # fmt: skip
ALWAYS_INCLUDE = {"data/README.md"}


def is_excluded(rel: str) -> bool:
    if rel in ALWAYS_INCLUDE:
        return False
    return any(fnmatch.fnmatch(rel, pattern) for pattern in EXCLUDE)


def is_hidden(rel: str) -> bool:
    return any(part.startswith(".") for part in Path(rel).parts)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scan(root: Path) -> dict[str, str]:
    """Relative path -> content hash for every file that belongs on GitHub."""
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            if not is_excluded(rel):
                files[rel] = _digest(path)
    return files


@dataclass
class UploadPlan:
    new: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    hidden: list[str] = field(default_factory=list)
    too_large: list[str] = field(default_factory=list)
    batches: list[Path] = field(default_factory=list)

    @property
    def files(self) -> list[str]:
        return sorted(self.new + self.changed)

    def __repr__(self) -> str:
        return self.describe()

    def describe(self) -> str:
        if not (self.files or self.deleted):
            return "Nothing to upload: GitHub already has the current version of every file."
        lines = [f"{len(self.new)} new and {len(self.changed)} changed file(s)."]
        for i, batch in enumerate(self.batches, 1):
            items = sorted(p.name for p in batch.iterdir())
            label = f"Upload {i} of {len(self.batches)}" if len(self.batches) > 1 else "Upload"
            lines.append(f"\n{label}: drag each item in {batch} onto GitHub -> Add file -> Upload files:")
            lines += [f"    {name}{'/' if (batch / name).is_dir() else ''}" for name in items]
        if self.hidden:
            lines.append(
                "\nHidden files (the uploader refuses these). On GitHub use Add file -> Create new file,"
            )
            lines.append(
                "type the path exactly as shown, and paste the file's contents (or edit the existing file):"
            )
            lines += [f"    {p}" for p in self.hidden]
        if self.too_large:
            lines.append("\nToo large for browser upload (over 25 MiB); these should not be in the repo:")
            lines += [f"    {p}" for p in self.too_large]
        if self.deleted:
            lines.append(
                "\nDeleted on your computer; delete them on GitHub too (open file -> ... -> Delete file):"
            )
            lines += [f"    {p}" for p in self.deleted]
        lines.append(
            "\nWhen everything is uploaded, run mark_uploaded() so the next bundle only has new changes."
        )
        return "\n".join(lines)


def _load_manifest(root: Path) -> dict[str, str]:
    path = root / MANIFEST
    return json.loads(path.read_text()) if path.exists() else {}


def _split(files: list[str], limit: int) -> list[list[str]]:
    """Batches of at most ``limit`` files, keeping each top-level folder together when it fits."""
    groups: dict[str, list[str]] = {}
    for rel in files:
        groups.setdefault(rel.split("/", 1)[0] if "/" in rel else "", []).append(rel)
    batches: list[list[str]] = [[]]
    for _, members in sorted(groups.items()):
        for start in range(0, len(members), limit):
            chunk = members[start : start + limit]
            if len(batches[-1]) + len(chunk) > limit:
                batches.append([])
            batches[-1].extend(chunk)
    return [b for b in batches if b]


def prepare_upload(root: Path | None = None, out_dir: str = OUT_DIR) -> UploadPlan:
    """Copy new and changed files into ``upload/`` (or ``upload/batch_N``) and describe what to do."""
    root = Path(root or repo_root())
    previous, current = _load_manifest(root), scan(root)
    plan = UploadPlan(
        new=sorted(set(current) - set(previous)),
        changed=sorted(k for k in current if k in previous and previous[k] != current[k]),
        deleted=sorted(set(previous) - set(current)),
    )
    plan.hidden = [p for p in plan.files if is_hidden(p)]
    plan.too_large = [p for p in plan.files if (root / p).stat().st_size > GITHUB_SIZE_LIMIT]
    regular = [p for p in plan.files if p not in plan.hidden and p not in plan.too_large]

    target = root / out_dir
    if target.exists():
        shutil.rmtree(target)
    batches = _split(regular, GITHUB_FILE_LIMIT)
    for i, batch in enumerate(batches, 1):
        base = target if len(batches) == 1 else target / f"batch_{i}"
        for rel in batch:
            dest = base / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / rel, dest)
        plan.batches.append(base)
    return plan


def mark_uploaded(root: Path | None = None) -> int:
    """Record the current state as uploaded. Returns the number of files tracked."""
    root = Path(root or repo_root())
    current = scan(root)
    (root / MANIFEST).write_text(json.dumps(current, indent=1, sort_keys=True))
    target = root / OUT_DIR
    if target.exists():
        shutil.rmtree(target)
    return len(current)
