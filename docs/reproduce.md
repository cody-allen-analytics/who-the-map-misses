# Reproduce

Three ways to run the project, from least to most setup.

## 1. In your browser (synthetic demo, nothing to install)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cody-allen-analytics/who-the-map-misses/blob/main/notebooks/01_demo.ipynb)

Runs the whole pipeline on synthetic data with planted biases, in about two minutes.

## 2. JupyterLab (the full analysis)

Requirements: Python 3.11 or newer, about 8 GB of RAM and 5 GB of disk, and for the satellite step a
Google Cloud project registered for Earth Engine (free for noncommercial use).

Open the project folder in JupyterLab and run the notebooks in order:

| Notebook | What it does | Time |
|---|---|---|
| `00_setup` | Installs dependencies, personalizes the files, runs the checks, puts the project on GitHub | 5 min |
| `01_demo` | Every step on synthetic data | 2 min |
| `02_ground_truth` | Downloads the census and the wealth map; builds and sanity-checks the tables | 15 min |
| `03_audit` | Audit of the Relative Wealth Index (H1, H2, H3, H6) and robustness | 5 min |
| `04_satellite_features` | Earth Engine export of AlphaEarth embeddings and night lights | 30-90 min (server side) |
| `05_challengers` | Survey simulation and challenger models (H4, H5) | 10-20 min |
| `06_report_and_release` | Final run, README findings, checks before sharing | 25 min |

Notebook 04 also runs well in Google Colab, where Earth Engine sign-in and Google Drive are built in.

## 3. Terminal

```bash
pip install -e ".[dev]"
mapaudit demo                 # synthetic run
mapaudit download             # real data into data/raw
mapaudit build && mapaudit audit && mapaudit robustness
mapaudit export-gee --project YOUR_PROJECT   # then download the CSVs into data/raw
mapaudit build && mapaudit simulate && mapaudit report
```

## Outputs

- `results/real/tables/*.csv`: every number in the write-up.
- `results/real/figures/*.png`: light and dark versions of every figure.
- `docs/results.md`: the generated results page.

Numbers in the documentation are produced by the report step; none are typed by hand.
