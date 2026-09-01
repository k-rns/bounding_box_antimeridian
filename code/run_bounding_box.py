import time

from bounding_box import (
    import_dataset_csv,
    points_for_map,
    calc_wrapped_bbox,
    split_polygon,
    build_final_bbox_geojson,
    export_geojson,
    export_plot_jpg,
    export_wkt,
    log_elapsed_time,
)
from set_paths import OUTPUTS_DIR
import dataset_configs


def main():

    dataset_config = dataset_configs.csv_998990
    
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    coords_df = import_dataset_csv(
        dataset_config["csv"],
        dataset_config["skiprows"],
        dataset_config["longitude"],
        dataset_config["latitude"],
        dataset_config["delimiter"]
    )

    points_gdf = points_for_map(coords_df, dataset_config["latitude"], dataset_config["longitude"])

    bbox_geojson, ogc_bbox = calc_wrapped_bbox(coords_df, dataset_config["longitude"], dataset_config["latitude"])
    split_geometries = split_polygon(bbox_geojson)
    final_bbox_geojson = build_final_bbox_geojson(split_geometries)

    export_geojson(final_bbox_geojson, dataset_config["id"], output_dir=OUTPUTS_DIR)
    export_plot_jpg(points_gdf, final_bbox_geojson, dataset_config["id"], output_dir=OUTPUTS_DIR)
    export_wkt(final_bbox_geojson, dataset_config["id"], output_dir=OUTPUTS_DIR)

    log_elapsed_time(start_time)    


if __name__ == "__main__":
    main()