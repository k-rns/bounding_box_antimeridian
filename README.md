# Bounding Box

[![Open Notebook](https://img.shields.io/badge/Open-Notebook-blue)](notebooks/demo_bounding_box.ipynb)
[![DOI](https://zenodo.org/badge/1353982774.svg)](https://doi.org/10.5281/zenodo.22239389)

This code computes a geographic bounding box for a tabular dataset containing a latitude and longitude column. Inputs are a CSV file, the column names for longitude and latitude, the field delimiter (comma, tab, semicolon, etc.), and a dataset id used to name output files. Coordinate values must be in decimal degrees, WGS84.

The code handles datasets in the -180/180 space, the 0/360 space, and datasets crossing the antimeridian (or both the antimeridian and prime meridian). The output is always a simple rectangular bounding box (or two rectangles joined as a MultiPolygon when it's split at the antimeridian), it does not support holes or more complex polygon shapes, just the smallest enclosing rectangle around the points.

The workflow loads a CSV file, extracts valid coordinate columns, calculates the smallest longitude interval containing the points, splits the bounding box if it crosses the antimeridian, and exports a GeoJSON file, a JPG preview map, and a WKT file. It also prints (but does not save) the OGC Bounding Box: [west, south, east, north].

## Setup

Install dependencies with:

```bash
pip install -r requirements.txt
```

Make sure you run this in the same Python environment you'll use to open the notebook — e.g. `conda activate <env_name>` before installing, then select that same environment as the kernel in Jupyter or VS Code. Then open [demo_bounding_box.ipynb](notebooks/demo_bounding_box.ipynb) in Jupyter or VS Code and run the cells.

## Code

- **`bounding_box.py`**: core library, loads and validates a CSV's coordinate columns, finds the tightest longitude interval (handling antimeridian wraparound), builds the rectangular bounding box geometry, splits it at the antimeridian if needed, and exports the result as GeoJSON, a JPG preview plot, and WKT.
- **`dataset_configs.py`**: example dataset configurations (CSV URL, delimiter, longitude/latitude column names, dataset id) used to run the pipeline against specific datasets.
- **`run_bounding_box.py`**: script entry point that runs the full pipeline end-to-end for a single dataset config, as an alternative to the notebook.
- **`set_paths.py`**: resolves the project root and defines the `code/`, `notebooks/`, and `output/` directory paths used by the other scripts.

## Folder Structure

```text
bounding_box/
├── code/
│   ├── bounding_box.py
│   ├── dataset_configs.py
│   ├── run_bounding_box.py
│   └── set_paths.py
├── notebooks/
│   └── demo_bounding_box.ipynb
├── outputs/
│   ├── output_dataset_<id>.geojson
│   └── output_dataset_<id>.jpg
|   |__ output_dataset_<id>.wkt
└── README.md
