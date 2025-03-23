import random
import math

# GeoJSON feature creation helper functions
def create_feature(geometry_type, coordinates, properties=None):
    """Create a GeoJSON feature with the specified geometry type and coordinates.

    Args:
        geometry_type (str): One of 'Point', 'LineString', 'Polygon', 'MultiPoint', etc.
        coordinates: The coordinates in the format required by the geometry type
        properties (dict, optional): Properties to include with the feature

    Returns:
        dict: A GeoJSON Feature object
    """
    return {
        "type": "Feature",
        "geometry": {
            "type": geometry_type,
            "coordinates": coordinates
        },
        "properties": properties or {}
    }


def create_point_feature(coords, properties=None):
    """Create a GeoJSON Point feature.

    Args:
        coords (list): [x, y] coordinates
        properties (dict, optional): Properties to include with the feature

    Returns:
        dict: A GeoJSON Point Feature
    """
    return create_feature("Point", coords, properties)


def create_multipoint_feature(coords_array, properties=None):
    """Create a GeoJSON MultiPoint feature.

    Args:
        coords_array (list): Array of [x, y] coordinates
        properties (dict, optional): Properties to include with the feature

    Returns:
        dict: A GeoJSON MultiPoint Feature
    """
    return create_feature("MultiPoint", coords_array, properties)


def create_linestring_feature(coords, properties=None):
    """Create a GeoJSON LineString feature.

    Args:
        coords (list): Array of [x, y] coordinates
        properties (dict, optional): Properties to include with the feature

    Returns:
        dict: A GeoJSON LineString Feature
    """
    return create_feature("LineString", coords, properties)


def create_multilinestring_feature(coords_array, properties=None):
    """Create a GeoJSON MultiLineString feature.

    Args:
        coords_array (list): Array of linestring coordinate arrays
        properties (dict, optional): Properties to include with the feature

    Returns:
        dict: A GeoJSON MultiLineString Feature
    """
    return create_feature("MultiLineString", coords_array, properties)


def create_polygon_feature(coords, properties=None):
    """Create a GeoJSON Polygon feature.

    Args:
        coords (list): Array of [x, y] coordinates representing a linear ring
                       (first and last points should be identical)
        properties (dict, optional): Properties to include with the feature

    Returns:
        dict: A GeoJSON Polygon Feature
    """
    # Ensure the polygon is closed (first point = last point)
    if coords[0] != coords[-1]:
        coords.append(coords[0])

    # In GeoJSON, polygon coordinates are an array of linear rings
    # The first ring is the exterior, any subsequent rings are holes
    return create_feature("Polygon", [coords], properties)


def create_polygon_with_holes_feature(exterior, holes=None, properties=None):
    """Create a GeoJSON Polygon feature with holes.

    Args:
        exterior (list): Array of [x, y] coordinates representing the exterior ring
        holes (list, optional): Array of arrays of coordinates representing holes
        properties (dict, optional): Properties to include with the feature

    Returns:
        dict: A GeoJSON Polygon Feature with holes
    """
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
    """Create a GeoJSON MultiPolygon feature.

    Args:
        polygons (list): Array of polygon coordinate arrays
                        (each polygon is an array of rings)
        properties (dict, optional): Properties to include with the feature

    Returns:
        dict: A GeoJSON MultiPolygon Feature
    """
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
    """Create a GeoJSON GeometryCollection feature.

    Args:
        geometries (list): Array of geometry objects
        properties (dict, optional): Properties to include with the feature

    Returns:
        dict: A GeoJSON Feature with a GeometryCollection
    """
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
    """Create a GeoJSON FeatureCollection.

    Args:
        features (list): Array of GeoJSON Feature objects

    Returns:
        dict: A GeoJSON FeatureCollection
    """
    return {
        "type": "FeatureCollection",
        "features": features
    }


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

