import random
import math
from functools import lru_cache
from pyproj import Transformer, CRS

# Default EPSG codes for coordinate systems
DEFAULT_SOURCE_EPSG = 4326  # WGS84 (lon/lat)
DEFAULT_TARGET_EPSG = 32630  # UTM zone 30N (meters)

# Global variables for EPSG configuration
_source_epsg = DEFAULT_SOURCE_EPSG
_target_epsg = DEFAULT_TARGET_EPSG


def set_epsg(source_epsg=None, target_epsg=None):
    """
    Set the EPSG codes for coordinate transformations.

    Args:
        source_epsg (int, optional): Source coordinate system EPSG code
        target_epsg (int, optional): Target coordinate system EPSG code

    Returns:
        dict: Current EPSG configuration
    """
    global _source_epsg, _target_epsg

    if source_epsg is not None:
        _source_epsg = source_epsg

    if target_epsg is not None:
        _target_epsg = target_epsg

    # Clear the transformer cache when changing settings
    _get_transformers.cache_clear()

    return {
        "source_epsg": _source_epsg,
        "target_epsg": _target_epsg
    }


def get_epsg():
    """
    Get the current EPSG code configuration.

    Returns:
        dict: Current EPSG configuration
    """
    return {
        "source_epsg": _source_epsg,
        "target_epsg": _target_epsg
    }


def get_epsg_info():
    """
    Get detailed information about the current EPSG codes.

    Returns:
        dict: Information about the current coordinate systems
    """
    source_crs = CRS.from_epsg(_source_epsg)
    target_crs = CRS.from_epsg(_target_epsg)

    return {
        "source": {
            "epsg": _source_epsg,
            "name": source_crs.name,
            "type": source_crs.type_name,
            "unit": source_crs.axis_info[0].unit_name
        },
        "target": {
            "epsg": _target_epsg,
            "name": target_crs.name,
            "type": target_crs.type_name,
            "unit": target_crs.axis_info[0].unit_name
        }
    }


def setup_utm_for_location(lon, lat, source_epsg=DEFAULT_SOURCE_EPSG):
    """
    Configure transformers with the appropriate UTM zone for a given location.

    Args:
        lon (float): Longitude
        lat (float): Latitude
        source_epsg (int, optional): Source EPSG code

    Returns:
        dict: Updated EPSG configuration
    """
    utm_epsg = get_utm_epsg_for_location(lon, lat)
    return set_epsg(source_epsg, utm_epsg)


def get_utm_zone_for_lon(lon):
    """Determine the UTM zone for a given longitude."""
    return int((lon + 180) / 6) + 1


def get_utm_epsg_for_location(lon, lat):
    """
    Get the appropriate UTM EPSG code for a given longitude and latitude.

    Args:
        lon (float): Longitude
        lat (float): Latitude

    Returns:
        int: EPSG code for the UTM zone
    """
    zone = get_utm_zone_for_lon(lon)

    # Northern hemisphere (including equator)
    if lat >= 0:
        return 32600 + zone
    # Southern hemisphere
    else:
        return 32700 + zone


# Cache the transformers for better performance
@lru_cache(maxsize=8)
def _get_transformers(source_epsg=None, target_epsg=None):
    """Get cached coordinate transformers for the given EPSG codes."""
    # Use global configuration if no specific codes provided
    source_epsg = source_epsg or _source_epsg
    target_epsg = target_epsg or _target_epsg

    source_crs = CRS.from_epsg(source_epsg)
    target_crs = CRS.from_epsg(target_epsg)

    to_target = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    to_source = Transformer.from_crs(target_crs, source_crs, always_xy=True)

    return to_target, to_source


# Coordinate transformation functions
def lonlat_to_utm(lon, lat, source_epsg=None, target_epsg=None):
    """Convert WGS84 (longitude, latitude) to UTM coordinates (meters)."""
    to_target, _ = _get_transformers(source_epsg, target_epsg)
    return to_target.transform(lon, lat)


def utm_to_lonlat(x, y, source_epsg=None, target_epsg=None):
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


def generate_rectangle_coordinates_lonlat(lon, lat, width_m, height_m, yaw=0, source_epsg=None, target_epsg=None):
    """Generate a rectangle with center at lon/lat with given dimensions."""
    x, y = lonlat_to_utm(lon, lat, source_epsg, target_epsg)

    agent_utm_coords = generate_rectangle_coordinates_utm(
        center_x=x,
        center_y=y,
        width_m=width_m,
        height_m=height_m,
        yaw=yaw
    )

    return utm_rectangle_to_lonlat(agent_utm_coords, source_epsg, target_epsg)


def utm_rectangle_to_lonlat(utm_points, source_epsg=None, target_epsg=None):
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


def utm_point_to_lonlat(utm_point, source_epsg=None, target_epsg=None):
    """Convert a single point from UTM to longitude/latitude."""
    return utm_to_lonlat(utm_point[0], utm_point[1], source_epsg, target_epsg)


def points_feature_collection(x_list, y_list, point_properties=None):
    """
    Create a GeoJSON FeatureCollection from lists of x and y coordinates.

    Args:
        x_list (list): List of x coordinates.
        y_list (list): List of y coordinates.
        point_properties (dict, optional): Properties to attach to each point feature.
    """
    points_features = []
    for x, y in zip(x_list, y_list):
        coords = [x, y]
        point_feature = create_point_feature(coords, point_properties)
        points_features.append(point_feature)

    return create_feature_collection(points_features)


def reproject_geometry(geometry, from_epsg, to_epsg):
    """
    Reproject GeoJSON geometry from one coordinate system to another.

    Args:
        geometry (dict): GeoJSON geometry to reproject
        from_epsg (int): Source EPSG code
        to_epsg (int): Target EPSG code

    Returns:
        dict: Reprojected GeoJSON geometry
    """
    geometry_type = geometry["type"]
    coordinates = geometry["coordinates"]

    # Set up transformer
    to_target, _ = _get_transformers(from_epsg, to_epsg)

    # Helper function to transform a single point
    def transform_point(point):
        return list(to_target.transform(point[0], point[1]))

    # Transform coordinates based on geometry type
    if geometry_type == "Point":
        new_coords = transform_point(coordinates)
    elif geometry_type == "MultiPoint" or geometry_type == "LineString":
        new_coords = [transform_point(point) for point in coordinates]
    elif geometry_type == "MultiLineString" or geometry_type == "Polygon":
        new_coords = [[transform_point(point) for point in line] for line in coordinates]
    elif geometry_type == "MultiPolygon":
        new_coords = [[[transform_point(point) for point in ring] for ring in polygon] for polygon in coordinates]
    else:
        raise ValueError(f"Unsupported geometry type: {geometry_type}")

    # Create a new geometry with transformed coordinates
    return {
        "type": geometry_type,
        "coordinates": new_coords
    }


def reproject_feature(feature, from_epsg, to_epsg):
    """
    Reproject a GeoJSON feature from one coordinate system to another.

    Args:
        feature (dict): GeoJSON feature to reproject
        from_epsg (int): Source EPSG code
        to_epsg (int): Target EPSG code

    Returns:
        dict: Reprojected GeoJSON feature
    """
    # Create a new feature with reprojected geometry
    new_feature = feature.copy()
    new_feature["geometry"] = reproject_geometry(feature["geometry"], from_epsg, to_epsg)

    return new_feature


def reproject_feature_collection(feature_collection, from_epsg, to_epsg):
    """
    Reproject a GeoJSON FeatureCollection from one coordinate system to another.

    Args:
        feature_collection (dict): GeoJSON FeatureCollection to reproject
        from_epsg (int): Source EPSG code
        to_epsg (int): Target EPSG code

    Returns:
        dict: Reprojected GeoJSON FeatureCollection
    """
    # Reproject each feature in the collection
    reprojected_features = [
        reproject_feature(feature, from_epsg, to_epsg)
        for feature in feature_collection["features"]
    ]

    # Create a new FeatureCollection with reprojected features
    return {
        "type": "FeatureCollection",
        "features": reprojected_features
    }


# Example usage - this will only run if the script is executed directly
if __name__ == "__main__":
    # Example 1: Default configuration
    print("Default EPSG configuration:", get_epsg())

    # Example 2: Change EPSG configuration
    set_epsg(4326, 32631)  # WGS84 to UTM zone 31N
    print("Updated EPSG configuration:", get_epsg())

    # Example 3: Auto-determine UTM zone based on location
    london_lon, london_lat = -0.1278, 51.5074
    setup_utm_for_location(london_lon, london_lat)
    print("London's UTM configuration:", get_epsg())
    print("CRS details:", get_epsg_info())

    # Example 4: Generate geometry with custom EPSG
    # Create a point in London
    london_point = create_point_feature([london_lon, london_lat], {"name": "London"})
    print("London point feature:", london_point)

    # Reproject to a different coordinate system
    reprojected_point = reproject_feature(london_point, 4326, 27700)  # OSGB 1936
    print("Reprojected to OSGB 1936:", reprojected_point)

    # Example 5: Create a rectangle around a specific location
    rectangle_coords = generate_rectangle_coordinates_lonlat(
        lon=london_lon,
        lat=london_lat,
        width_m=500,  # 500m width
        height_m=300  # 300m height
    )
    rectangle_feature = create_polygon_feature(rectangle_coords, {"name": "London Area"})
    print("Rectangle feature:", rectangle_feature)