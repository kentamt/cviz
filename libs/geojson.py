import random
import math
from functools import lru_cache
from pyproj import Transformer, CRS

# Default EPSG codes
DEFAULT_SOURCE_EPSG = 4326  # WGS84 (lon/lat)
DEFAULT_TARGET_EPSG = 32630  # UTM zone 30N (meters)


# Cache the transformers for better performance
@lru_cache(maxsize=8)
def _get_transformers(source_epsg=DEFAULT_SOURCE_EPSG, target_epsg=DEFAULT_TARGET_EPSG):
    """Get cached coordinate transformers for the given EPSG codes."""
    source_crs = CRS.from_epsg(source_epsg)
    target_crs = CRS.from_epsg(target_epsg)

    to_target = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    to_source = Transformer.from_crs(target_crs, source_crs, always_xy=True)

    return to_target, to_source


# Coordinate transformation functions
def lonlat_to_utm(lon, lat, source_epsg=DEFAULT_SOURCE_EPSG, target_epsg=DEFAULT_TARGET_EPSG):
    """Convert WGS84 (longitude, latitude) to UTM coordinates (meters)."""
    to_target, _ = _get_transformers(source_epsg, target_epsg)
    return to_target.transform(lon, lat)


def utm_to_lonlat(x, y, source_epsg=DEFAULT_SOURCE_EPSG, target_epsg=DEFAULT_TARGET_EPSG):
    """Convert UTM coordinates (meters) to WGS84 (longitude, latitude)."""
    _, to_source = _get_transformers(source_epsg, target_epsg)
    return to_source.transform(x, y)


# Feature creation functions
def create_feature(geometry_type, coordinates, properties=None):
    """Create a GeoJSON feature with the specified geometry type and coordinates."""
    return {
        "type": "Feature",
        "geometry": {
            "type": geometry_type,
            "coordinates": coordinates
        },
        "properties": properties or {}
    }


def create_point_feature(coords, properties=None):
    """Create a GeoJSON Point feature."""
    return create_feature("Point", coords, properties)


def create_multipoint_feature(coords_array, properties=None):
    """Create a GeoJSON MultiPoint feature."""
    return create_feature("MultiPoint", coords_array, properties)


def create_linestring_feature(coords, properties=None):
    """Create a GeoJSON LineString feature."""
    return create_feature("LineString", coords, properties)


def create_multilinestring_feature(coords_array, properties=None):
    """Create a GeoJSON MultiLineString feature."""
    return create_feature("MultiLineString", coords_array, properties)


def create_polygon_feature(coords, properties=None):
    """Create a GeoJSON Polygon feature."""
    # Ensure the polygon is closed (first point = last point)
    if coords[0] != coords[-1]:
        coords.append(coords[0])

    # In GeoJSON, polygon coordinates are an array of linear rings
    # The first ring is the exterior, any subsequent rings are holes
    return create_feature("Polygon", [coords], properties)


def create_polygon_with_holes_feature(exterior, holes=None, properties=None):
    """Create a GeoJSON Polygon feature with holes."""
    # Ensure the exterior ring is closed
    if exterior[0] != exterior[-1]:
        exterior.append(exterior[0])

    # Create the coordinate array with the exterior ring first
    polygon_coords = [exterior]

    # Add any holes
    if holes:
        for hole in holes:
            # Ensure each hole is closed
            if hole[0] != hole[-1]:
                hole.append(hole[0])
            polygon_coords.append(hole)

    return create_feature("Polygon", polygon_coords, properties)


def create_multipolygon_feature(polygons, properties=None):
    """Create a GeoJSON MultiPolygon feature."""
    # Ensure each polygon is properly formatted
    formatted_polygons = []

    for polygon in polygons:
        # If this is just a simple array of coordinates (exterior ring only)
        if all(isinstance(coord, (int, float)) for coord in polygon[0]):
            # Ensure it's closed
            if polygon[0] != polygon[-1]:
                polygon.append(polygon[0])
            formatted_polygons.append([polygon])
        else:
            # This is already an array of rings
            exterior = polygon[0]
            if exterior[0] != exterior[-1]:
                exterior.append(exterior[0])

            rings = [exterior]

            # Add any holes (if present)
            for i in range(1, len(polygon)):
                hole = polygon[i]
                if hole[0] != hole[-1]:
                    hole.append(hole[0])
                rings.append(hole)

            formatted_polygons.append(rings)

    return create_feature("MultiPolygon", formatted_polygons, properties)


def create_geometry_collection_feature(geometries, properties=None):
    """Create a GeoJSON GeometryCollection feature."""
    # Create a GeoJSON GeometryCollection
    geometry_collection = {
        "type": "GeometryCollection",
        "geometries": geometries
    }

    # Create the feature
    return {
        "type": "Feature",
        "geometry": geometry_collection,
        "properties": properties or {}
    }


def create_feature_collection(features):
    """Create a GeoJSON FeatureCollection."""
    return {
        "type": "FeatureCollection",
        "features": features
    }


# Geometry generation functions
def generate_rectangle_coordinates(center_x=300, center_y=300, w=100, h=100, yaw=0):
    """Generate a rectangle polygon as GeoJSON coordinates array."""
    coords = [
        [center_x + w * math.cos(yaw) - h * math.sin(yaw), center_y + w * math.sin(yaw) + h * math.cos(yaw)],
        [center_x - w * math.cos(yaw) - h * math.sin(yaw), center_y - w * math.sin(yaw) + h * math.cos(yaw)],
        [center_x - w * math.cos(yaw) + h * math.sin(yaw), center_y - w * math.sin(yaw) - h * math.cos(yaw)],
        [center_x + w * math.cos(yaw) + h * math.sin(yaw), center_y + w * math.sin(yaw) - h * math.cos(yaw)],
        # Close the ring by repeating the first point
        [center_x + w * math.cos(yaw) - h * math.sin(yaw), center_y + w * math.sin(yaw) + h * math.cos(yaw)]
    ]

    return coords


def generate_random_point(center_x=300, center_y=300, radius=30):
    """Generate a random point near a center with specified radius."""
    angle = random.uniform(0, 2 * math.pi)
    distance = random.uniform(0, radius)

    x = center_x + distance * math.cos(angle)
    y = center_y + distance * math.sin(angle)

    return [x, y]


def generate_rectangle_coordinates_utm(center_x, center_y, width_m, height_m, yaw=0):
    """Generate a rectangle polygon in UTM coordinates (meters)."""
    points = [
        [
            center_x + width_m * math.cos(yaw) - height_m * math.sin(yaw),
            center_y + width_m * math.sin(yaw) + height_m * math.cos(yaw)
        ],
        [
            center_x - width_m * math.cos(yaw) - height_m * math.sin(yaw),
            center_y - width_m * math.sin(yaw) + height_m * math.cos(yaw)
        ],
        [
            center_x - width_m * math.cos(yaw) + height_m * math.sin(yaw),
            center_y - width_m * math.sin(yaw) - height_m * math.cos(yaw)
        ],
        [
            center_x + width_m * math.cos(yaw) + height_m * math.sin(yaw),
            center_y + width_m * math.sin(yaw) - height_m * math.cos(yaw)
        ]
    ]
    return points

def generate_rectangle_coordinates_lonlat(lon, lat, width_m, height_m, yaw=0):
    x, y = lonlat_to_utm(lon, lat)

    agent_utm_coords = generate_rectangle_coordinates_utm(
        center_x=x,
        center_y=y,
        width_m=width_m,
        height_m=height_m,
        yaw=yaw
    )

    return utm_rectangle_to_lonlat(agent_utm_coords)

def utm_rectangle_to_lonlat(utm_points, source_epsg=DEFAULT_SOURCE_EPSG, target_epsg=DEFAULT_TARGET_EPSG):
    """Convert rectangle points from UTM to longitude/latitude and close the polygon."""
    source_points = [utm_to_lonlat(p[0], p[1], source_epsg, target_epsg) for p in utm_points]

    # Close the polygon by repeating the first point
    source_points.append(source_points[0])

    return source_points


def generate_random_point_utm(center_x, center_y, radius_m=300):
    """Generate a random point near a center in UTM coordinates (meters)."""
    angle = random.uniform(0, 2 * math.pi)
    distance = random.uniform(0, radius_m)

    x = center_x + distance * math.cos(angle)
    y = center_y + distance * math.sin(angle)

    return [x, y]


def utm_point_to_lonlat(utm_point, source_epsg=DEFAULT_SOURCE_EPSG, target_epsg=DEFAULT_TARGET_EPSG):
    """Convert a single point from UTM to longitude/latitude."""
    return utm_to_lonlat(utm_point[0], utm_point[1], source_epsg, target_epsg)
