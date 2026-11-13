"""Tests for the no-git workflow helpers: upload bundles, personalization, checks, README updates."""

from pathlib import Path

import pytest

from mapaudit import notebook as nb
from mapaudit.upload import _split, is_excluded, is_hidden, mark_uploaded, prepare_upload

FILES = {
    "README.md": "# x\nhttps://github.com/YOUR-USERNAME/repo\n",
    "src/pkg/a.py": "PLACEHOLDER = 'YOUR-USERNAME'  # code must keep its placeholder strings\n",
    "docs/index.md": "hello\n",
    ".github/workflows/ci.yml": "name: CI\n",
    "data/README.md": "data readme\n",
    "data/raw/big.csv": "x\n",
    "results/demo/t.csv": "1\n",
    "results/real/tables/t.csv": "1\n",
    "src/pkg/__pycache__/a.cpython-312.pyc": "bytecode",
    "notebooks/.ipynb_checkpoints/x-checkpoint.ipynb": "{}",
    "LICENSE": "Copyright (c) 2026 YOUR NAME\n",
    "CITATION.cff": (
        'authors:\n  - family-names: "YOUR-FAMILY-NAME"\n    given-names: "YOUR NAME"\n'
        '    orcid: "https://orcid.org/0000-0000-0000-0000"\n'
    ),
    "pyproject.toml": 'authors = [{ name = "YOUR NAME", email = "you@example.com" }]\n',
}


def _make_repo(root: Path) -> None:
    for rel, text in FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def test_exclusion_rules_mirror_gitignore():
    assert is_excluded("data/raw/big.csv") and not is_excluded("data/README.md")
    assert is_excluded("results/demo/t.csv") and not is_excluded("results/real/tables/t.csv")
    assert is_excluded("src/pkg/__pycache__/a.cpython-312.pyc")
    assert is_excluded("notebooks/.ipynb_checkpoints/x-checkpoint.ipynb")
    assert is_hidden(".github/workflows/ci.yml") and not is_hidden("docs/index.md")


def test_upload_bundle_tracks_new_changed_and_deleted_files(tmp_path):
    _make_repo(tmp_path)
    plan = prepare_upload(tmp_path)
    assert "data/README.md" in plan.new and "data/raw/big.csv" not in plan.new
    assert plan.hidden == [".github/workflows/ci.yml"]
    assert (tmp_path / "upload" / "README.md").exists()
    assert not (tmp_path / "upload" / ".github").exists()  # hidden files are listed, not staged

    mark_uploaded(tmp_path)
    assert not (tmp_path / "upload").exists()
    assert "Nothing to upload" in prepare_upload(tmp_path).describe()

    (tmp_path / "docs" / "index.md").write_text("changed\n")
    (tmp_path / "src" / "pkg" / "a.py").unlink()
    plan = prepare_upload(tmp_path)
    assert plan.changed == ["docs/index.md"] and plan.new == []
    assert plan.deleted == ["src/pkg/a.py"]
    assert (tmp_path / "upload" / "docs" / "index.md").read_text() == "changed\n"
    assert "delete them on GitHub" in plan.describe()


def test_batches_respect_githubs_100_file_limit():
    files = [f"docs/f{i:03d}.md" for i in range(150)] + ["README.md", "src/a.py"]
    batches = _split(files, 100)
    assert all(len(batch) <= 100 for batch in batches)
    assert sorted(f for batch in batches for f in batch) == sorted(files)


def test_personalize_replaces_placeholders_but_leaves_code_alone(tmp_path):
    _make_repo(tmp_path)
    changed = nb.personalize("octocat", "Ada", "Lovelace", "ada@example.org", root=tmp_path)
    assert "README.md" in changed and "src/pkg/a.py" not in changed
    cff = (tmp_path / "CITATION.cff").read_text()
    assert 'given-names: "Ada"' in cff and 'family-names: "Lovelace"' in cff and "orcid" not in cff
    assert "Ada Lovelace" in (tmp_path / "LICENSE").read_text()
    assert "ada@example.org" in (tmp_path / "pyproject.toml").read_text()
    assert "github.com/octocat/repo" in (tmp_path / "README.md").read_text()
    assert "YOUR-USERNAME" in (tmp_path / "src" / "pkg" / "a.py").read_text()


def test_sanity_checks_flag_implausible_builds():
    good = {
        "localities": 189_000,
        "population": 126e6,
        "rwi_quadkey_consistency": 0.99,
        "label_loadings": {"wealth_dhs_like": {"a": 0.3}, "marg_index": {"b": 0.2}},
    }
    assert (nb.sanity_checks(good)["result"] == "pass").all()
    assert (nb.sanity_checks({**good, "localities": 5_000})["result"] == "CHECK").any()


def test_update_readme_inserts_findings_and_figure(tmp_path):
    (tmp_path / "README.md").write_text(
        "A\n<!-- FINDINGS:START (x) -->\nStatus: in progress\n<!-- FINDINGS:END -->\n\n"
        "<!-- FIGURE:START (y) -->\n\n<!-- FIGURE:END -->\nB\n"
    )
    (tmp_path / "results" / "real").mkdir(parents=True)
    (tmp_path / "results" / "real" / "headline.md").write_text("- **Finding.** 42\n")
    figures = tmp_path / "docs" / "assets" / "figures" / "real"
    figures.mkdir(parents=True)
    (figures / "decile_errors.png").write_bytes(b"png")
    nb.update_readme(tmp_path)
    text = (tmp_path / "README.md").read_text()
    assert "- **Finding.** 42" in text and "Status: in progress" not in text
    assert "<picture>" in text and text.endswith("B\n")


def test_notebook_mode_reads_environment(monkeypatch):
    monkeypatch.setenv("MAPAUDIT_NOTEBOOK_MODE", "demo")
    assert nb.notebook_mode() == "demo"
    monkeypatch.setenv("MAPAUDIT_NOTEBOOK_MODE", "nonsense")
    with pytest.raises(ValueError):
        nb.notebook_mode()
