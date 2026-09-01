import json
import pandas as pd
import geopandas as gpd
import os
from shapely.geometry import shape, box, mapping, Point, Polygon, GeometryCollection, LineString
from shapely.geometry.polygon import orient
from shapely import affinity
from shapely.ops import split
import matplotlib.pyplot as plt
import time


def import_dataset_csv(csv: str, skiprows: int, longitude: str, latitude: str, delimiter: str):
    """
    Generic CSV import for tabular datasets.

    Returns: pandas dataframe with only longitude and latitude columns
    """
    df = pd.read_csv(
        filepath_or_buffer=csv,
        skiprows=skiprows,
        sep=delimiter
    )

    print(df.head())
    print(df.columns)

    if longitude not in df.columns:
        raise ValueError(f"Longitude column '{longitude}' not found in dataset")

    if latitude not in df.columns:
        raise ValueError(f"Latitude column '{latitude}' not found in dataset")

    coords_df = df[[longitude, latitude]].copy()

    coords_df[longitude] = pd.to_numeric(coords_df[longitude], errors="coerce")
    coords_df[latitude] = pd.to_numeric(coords_df[latitude], errors="coerce")
    coords_df = coords_df.dropna(subset=[longitude, latitude])

    if coords_df.empty:
        raise ValueError("No valid latitude/longitude rows found in dataset")

    # Validate longitude values.
    # This allows both common longitude conventions:
    # - standard geographic longitudes: [-180, 180]
    # - 0 to 360 degree longitudes: [0, 360]
    lon_values = coords_df[longitude]

    is_valid_standard_lon = lon_values.between(-180, 180)
    is_valid_360_lon = lon_values.between(0, 360)

    is_valid_lon = is_valid_standard_lon | is_valid_360_lon

    if not is_valid_lon.all():
        bad_longitudes = lon_values[~is_valid_lon]

        print("Invalid longitude values:")
        print(bad_longitudes.head())

        raise ValueError("Longitude values must be within [-180, 180] or [0, 360]")
    
        
    invalid_lat = (coords_df[latitude] < -90) | (coords_df[latitude] > 90)
    if invalid_lat.any():
        print (invalid_lat)
        raise ValueError("Latitude values must be within [-90, 90]")

    print ("This is the coords_df", coords_df.head(), type(coords_df))
    return coords_df

def points_for_map (coords_df, latitude, longitude):
    '''
    Normalizes longitudinal values to [-180, 180] frame

    Input: pandas dataframe with longitude and latitude columns (checked & cleaned by import dataset csv)
    Output: Geopandas dataframe(lat/lon) of points
    '''
     
    # Normalize longitude values in the [-180, 180] frame
    coords_df = coords_df.copy()
    coords_df["lon_plot"] = ((coords_df[longitude] + 180) % 360) - 180

    points_gdf = gpd.GeoDataFrame(
        coords_df,
        geometry=gpd.points_from_xy(coords_df["lon_plot"], coords_df[latitude]),
        crs="EPSG:4326")
    
    print(points_gdf.head())
    return points_gdf

def find_best_longitude_interval(longitudes):
    """
    Find the tightest continuous longitude interval containing all points, treating longitude as circular data.

    Input: pandas.Series:  longitudinal values such as coords_df[longitude]
    Output: pandas.Seroes: original longitudes shifted into the best continuous interval for bbox computation

    """

    # Convert all longitudes into a 0 to 360 representation & sort them for gaps to be checked in order
    lon_360 = longitudes % 360
    lon_sorted = sorted(lon_360)

    # handles only 1 longitude
    if len(lon_sorted) == 1:
        return lon_360

    # compute and store all gaps between neighboring longitudes
    gaps = []
    for i in range(len(lon_sorted) - 1):
        gap = lon_sorted[i + 1] - lon_sorted[i]
        gaps.append((gap, lon_sorted[i], lon_sorted[i + 1]))

    # Also compute the wraparound gap from the last value back to the first.
    wrap_gap = (lon_sorted[0] + 360) - lon_sorted[-1]
    gaps.append((wrap_gap, lon_sorted[-1], lon_sorted[0] + 360))

    # Find the largest empty gap and use its end as the cut point.
    largest_gap, gap_start, gap_end = max(gaps, key=lambda x: x[0])
    cut = gap_end % 360

    # Move values before the cut forward by 360 to make one continuous interval.
    # Added a mask here because of dataset 986627, cut wrong because of floating number issues: 153.9994 < 153.99940000000004 (accidently true, so cut was wrong)  153.9994 < 153.99940000000004 - 1e-9 is False so 153.9994 no longer gets incorrectly shifted
    epsilon = 1e-9
    shifted = lon_360.copy() #make copy
    mask = shifted < cut - epsilon
    # shifted = shifted.apply(lambda x: x + 360 if x < cut else x)
    #shifted[shifted < cut] = shifted[shifted < cut] + 360
    shifted.loc[mask] = shifted.loc[mask] + 360
 


    interval_start = shifted.min()
    interval_end = shifted.max()

    print("best longitude interval start:", interval_start)
    print("best longitude interval end:", interval_end)

    return shifted

def calc_wrapped_bbox (coords_df, longitude, latitude):
    '''
    Calculate bounding-box outputs from cleaned latitude/longitude data.

    Input: pandas dataframe with longitude and latitude columns (checked & cleaned by import dataset csv)
    Outputs: 
        * Python dictionary representing a GeoJSON geometry (didn't want to work with shapely object)
        * OGC-style bounding box list in the format: [west, south, east, north]

    Notes:
    - The OGC bbox values are normalized to the standard [-180, 180] longitude frame.
    - For antimeridian-crossing boxes, west may be greater than east. Example: [170, 10, -170, 25]
    '''
    coords_df = coords_df.copy()

    shifted_longitudes = find_best_longitude_interval(coords_df[longitude])
    coords_df["longitude_for_bbox"] = shifted_longitudes

    #compute bounding geometry
    west_raw = coords_df["longitude_for_bbox"].min() #minx
    east_raw = coords_df["longitude_for_bbox"].max() #maxx
    south = float(coords_df[latitude].min()) #miny
    north = float(coords_df[latitude].max()) #maxy

    #convert west and east to -180/180 frame for OGC bounding box return
    west = float(((west_raw + 180) % 360) - 180)
    east = float(((east_raw + 180) % 360) - 180)

    ogc_bbox = [west, south, east, north]

    if west_raw == east_raw and south == north:
        bb_geojson = {
            "type": "Point",
            "coordinates": [west, south]}

    else:
        bounding_box = box(west_raw, south, east_raw, north)
        bb_geojson = mapping(bounding_box)
        
    print("bounding box to analyse: ", bb_geojson, type(bb_geojson))
    print("  OGC Bounding Box [west, south, east, north]:", ogc_bbox)
    return bb_geojson, ogc_bbox

def split_polygon(geojson: dict):
    """
    Split a wrapped bounding-box polygon at the antimeridian if needed.

    Input: Python dictionary representing a GeoJSON geometry
    Output: list of GeoJSON dicts
    """
    if geojson["type"] != "Polygon":
        return [geojson]

    if not geojson["coordinates"]:
        print("No coordinates in dictionary")
        return []

    shell = geojson["coordinates"][0] #only boundinx box, which is first ring

    if not shell:
        return []

    ring_minx = min(coord[0] for coord in shell)
    ring_maxx = max(coord[0] for coord in shell)

    if ring_minx < -180 and ring_maxx > 180:
        raise NotImplementedError("Splitting by multiple meridians is not supported.")

    if ring_minx < -180:
        splitter = LineString([[-180, -90.0], [-180, 90.0]])
        split_polygons = split(Polygon(shell), splitter)
    elif ring_maxx > 180:
        splitter = LineString([[180, -90.0], [180, 90.0]])
        split_polygons = split(Polygon(shell), splitter)
    else:
        split_polygons = GeometryCollection([Polygon(shell)])

    return translate_polygons(split_polygons)

def translate_polygons(geometry_collection: GeometryCollection):
    """
    Translate polygons back into the standard GeoJSON longitude range [-180, 180]
    and return GeoJSON dictionaries.

    Input: geometry collection
    Output: list of GeoJSON dicts

    """
    translated =[]

    for polygon in geometry_collection.geoms:
        minx, miny, maxx, maxy = polygon.bounds

        if minx < -180:
            geo_polygon = affinity.translate(polygon, xoff=360)
        elif maxx > 180:
            geo_polygon = affinity.translate(polygon, xoff=-360)
        else:
            geo_polygon = polygon

        translated.append(mapping(geo_polygon))
    
    return translated

def build_final_bbox_geojson(geometries):
    """
    Return a final GeoJSON geometry from a list of geometry dicts (Can be multipolygon, polygon or point).

    The final geometry is oriented so polygon exterior rings follow the GeoJSON/RFC 7946 right-hand rule.
    """
    if not geometries:
        raise ValueError("No geometries provided")

    if len(geometries) == 1:
        final_bbox_geojson = geometries[0]
    else:
        final_bbox_geojson = {
            "type": "MultiPolygon",
            "coordinates": [geometry["coordinates"] for geometry in geometries]
        }

    # force right hand rule for Geojson geometries (exterior rings should be counterclockwise, interior rings should be clockwise)
    shapely_geometry = shape(final_bbox_geojson)

    if shapely_geometry.geom_type in ["Polygon", "MultiPolygon"]:
        shapely_geometry = orient(shapely_geometry, sign=1.0)
    
    final_bbox_geojson = mapping(shapely_geometry)

    print("Final bbox GeoJSON: ", final_bbox_geojson) 

    return final_bbox_geojson


def export_geojson(final_bbox_geojson, dataset_id, output_dir=None):
    """
    Save a final GeoJSON geometry dict to a .geojson file.

    Input:
    - final_bbox_geojson: one GeoJSON geometry dict (returned by build_final_bbox_geojson())
    - dataset_id: dataset identifier used in the output filename
    - output_dir: optional output directory
    """
    if not final_bbox_geojson:
        raise ValueError("No GeoJSON geometry provided")

    if output_dir is None:
        output_dir = os.getcwd()

    output_path = os.path.join(output_dir, f"output_dataset_{dataset_id}.geojson")

    with open(output_path, "w") as f:
        json.dump(final_bbox_geojson, f)

    print("Saved file to", output_path)

def export_plot_jpg(points_gdf, final_bbox_geojson, dataset_id, output_dir=None):
    """
    Export a JPG plot of the dataset points and final GeoJSON-safe bbox.
    """
    if output_dir is None:
        output_dir = os.getcwd()

    output_path = os.path.join(output_dir, f"output_dataset_{dataset_id}.jpg")

    fig, ax = plt.subplots(figsize=(14, 7))

    geom_type = final_bbox_geojson["type"]

    if geom_type == "Point":
        shapes = [Point(final_bbox_geojson["coordinates"])]
    elif geom_type == "Polygon":
        shapes = [Polygon(final_bbox_geojson["coordinates"][0])]
    elif geom_type == "MultiPolygon":
        shapes = [Polygon(poly[0]) for poly in final_bbox_geojson["coordinates"]]
    else:
        raise ValueError(f"Unsupported geometry type for plotting: {geom_type}")

    if shapes:
        geo_series = gpd.GeoSeries(shapes, crs="EPSG:4326")

        if geom_type == "Point":
            geo_series.plot(ax=ax, markersize=60, color="blue")
        else:
            geo_series.boundary.plot(ax=ax, linewidth=2)

    points_gdf.plot(ax=ax, markersize=8, color="red")

    ax.set_title(f"Dataset {dataset_id}")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)

    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print("Saved plot to", output_path)

def export_wkt(final_bbox_geojson, dataset_id, output_dir=None):
    """
    Save a final GeoJSON geometry dict to a .wkt file.
    """
    if not final_bbox_geojson:
        raise ValueError("No GeoJSON geometry provided")

    if output_dir is None:
        output_dir = os.getcwd()

    output_path = os.path.join(output_dir, f"output_dataset_{dataset_id}.wkt")

    shapely_geometry = shape(final_bbox_geojson)

    with open(output_path, "w") as f:
        f.write(shapely_geometry.wkt)

    print("Saved WKT file to", output_path)

def log_elapsed_time(start_time):
    """
    Print how long the script took to run.
    """
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = elapsed % 60

    if minutes > 0:
        print(f"Total runtime: {minutes} min {seconds:.2f} sec")
    else:
        print(f"Total runtime: {seconds:.2f} seconds")


