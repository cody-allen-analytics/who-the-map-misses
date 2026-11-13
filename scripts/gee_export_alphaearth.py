"""Terminal entry point for the Earth Engine export; the logic lives in mapaudit/gee.py.

    python scripts/gee_export_alphaearth.py --project YOUR_GCP_PROJECT --dry-run
    python scripts/gee_export_alphaearth.py --project YOUR_GCP_PROJECT

In JupyterLab, use notebooks/04_satellite_features.ipynb instead.
"""

import sys

from mapaudit.gee import main

if __name__ == "__main__":
    sys.exit(main())
