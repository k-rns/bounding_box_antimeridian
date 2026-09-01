# Bounding Box

[![Open Notebook](https://img.shields.io/badge/Open-Notebook-blue)](notebooks/demo_bounding_box.ipynb)

This code computes geographic bounding boxes for BCO-DMO datasets containing latitude and longitude values. Inputs are the link to the csv file, dataset id and name of longitude and latitude columns. Coordinate values in the .csv file need to be in decimal degrees in WGS84 coordinate reference system. 

The code can handle datasets in the -180/180 space, datasets in the 0/360 space and datasets crossing the antimeridian (or both prime and antimeridian).

The workflow loads a CSV file, extracts valid coordinate columns, calculates the smallest longitude interval containing the points, splits the bounding box if it crosses the antimeridian, and exports a GeoJSON file, JPG preview map and wkt. Print out (not saved) that is currently useful as well is the OGC Bounding Box [west, south, east, north].

## Setup

Install dependencies with:

```bash
pip install -r requirements.txt
```

Then open [demo_bounding_box.ipynb](notebooks/demo_bounding_box.ipynb) in Jupyter or VS Code and run the cells.

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