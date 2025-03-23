import random
import math
from pyproj import Transformer, CRS


class GeoJSONHelper:

    def __init__(self, source_epsg=4326, target_epsg=32630):
        """Initialize the GeoJSONHelper with specified EPSG codes.

        Args:
            source_epsg (int): Source EPSG code. Default is 4326 (WGS84 - longitude, latitude).
            target_epsg (int): Target EPSG code. Default is 32630 (UTM zone 30N - meters).
        """
        # Define projection systems based on provided EPSG codes
        self.source_crs = CRS.from_epsg(source_epsg)
        self.target_crs = CRS.from_epsg(target_epsg)

        # Create transformers for converting between coordinate systems
        self.to_target = Transformer.from_crs(self.source_crs, self.target_crs, always_xy=True)
        self.to_source = Transformer.from_crs(self.target_crs, self.source_crs, always_xy=True)

    # GeoJSON feature creation helper functions
    def create_feature(self, geometry_type, coordinates, properties=None):
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

    def create_point_feature(self, coords, properties=None):
        """Create a GeoJSON Point feature.

        Args:
            coords (list): [x, y] coordinates
            properties (dict, optional): Properties to include with the feature

        Returns:
            dict: A GeoJSON Point Feature
        """
        return self.create_feature("Point", coords, properties)

    def create_multipoint_feature(self, coords_array, properties=None):
        """Create a GeoJSON MultiPoint feature.

        Args:
            coords_array (list): Array of [x, y] coordinates
            properties (dict, optional): Properties to include with the feature

        Returns:
            dict: A GeoJSON MultiPoint Feature
        """
        return self.create_feature("MultiPoint", coords_array, properties)

    def create_linestring_feature(self, coords, properties=None):
        """Create a GeoJSON LineString feature.

        Args:
            coords (list): Array of [x, y] coordinates
            properties (dict, optional): Properties to include with the feature

        Returns:
            dict: A GeoJSON LineString Feature
        """
        return self.create_feature("LineString", coords, properties)

    def create_multilinestring_feature(self, coords_array, properties=None):
        """Create a GeoJSON MultiLineString feature.

        Args:
            coords_array (list): Array of linestring coordinate arrays
            properties (dict, optional): Properties to include with the feature

        Returns:
            dict: A GeoJSON MultiLineString Feature
        """
        return self.create_feature("MultiLineString", coords_array, properties)

    def create_polygon_feature(self, coords, properties=None):
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
        return self.create_feature("Polygon", [coords], properties)

    def create_polygon_with_holes_feature(self, exterior, holes=None, properties=None):
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

        return self.create_feature("Polygon", polygon_coords, properties)

    def create_multipolygon_feature(self, polygons, properties=None):
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

        return self.create_feature("MultiPolygon", formatted_polygons, properties)

    def create_geometry_collection_feature(self, geometries, properties=None):
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

    def create_feature_collection(self, features):
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

    def generate_rectangle_coordinates(self, center_x=300, center_y=300, w=100, h=100, yaw=0):
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

    def generate_random_point(self, center_x=300, center_y=300, radius=30):
        """Generate a random point near a center with specified radius."""
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(0, radius)

        x = center_x + distance * math.cos(angle)
        y = center_y + distance * math.sin(angle)

        return [x, y]

    def source_to_target(self, x, y):
        """Convert source CRS coordinates to target CRS coordinates.
        By default this converts WGS84 (longitude, latitude) to UTM coordinates (meters)
        """
        return self.to_target.transform(x, y)

    def target_to_source(self, x, y):
        """Convert target CRS coordinates to source CRS coordinates.
        By default this converts UTM coordinates (meters) to WGS84 (longitude, latitude)
        """
        return self.to_source.transform(x, y)

    def generate_rectangle_coordinates_target(self, center_x, center_y, width_m, height_m, yaw=0):
        """Generate a rectangle polygon in target CRS coordinates (typically meters)"""
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

    def target_rectangle_to_source(self, target_points):
        """Convert rectangle points from target CRS to source CRS and close the polygon.
        By default this converts from UTM to longitude/latitude.
        """
        source_points = [self.target_to_source(p[0], p[1]) for p in target_points]

        # Close the polygon by repeating the first point
        source_points.append(source_points[0])

        return source_points

    def generate_random_point_target(self, center_x, center_y, radius_m=300):
        """Generate a random point near a center in target CRS coordinates (typically meters)"""
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(0, radius_m)

        x = center_x + distance * math.cos(angle)
        y = center_y + distance * math.sin(angle)

        return [x, y]

    def target_point_to_source(self, target_point):
        """Convert a single point from target CRS to source CRS
        By default this converts from UTM to longitude/latitude
        """
        return self.target_to_source(target_point[0], target_point[1])

    # For backward compatibility, keep the old method names as aliases
    def utm_to_lonlat(self, x, y):
        """Alias for target_to_source for backward compatibility"""
        return self.target_to_source(x, y)

    def lonlat_to_utm(self, lon, lat):
        """Alias for source_to_target for backward compatibility"""
        return self.source_to_target(lon, lat)

    def generate_rectangle_coordinates_utm(self, center_x, center_y, width_m, height_m, yaw=0):
        """Alias for generate_rectangle_coordinates_target for backward compatibility"""
        return self.generate_rectangle_coordinates_target(center_x, center_y, width_m, height_m, yaw)

    def utm_rectangle_to_lonlat(self, utm_points):
        """Alias for target_rectangle_to_source for backward compatibility"""
        return self.target_rectangle_to_source(utm_points)

    def generate_random_point_utm(self, center_x, center_y, radius_m=300):
        """Alias for generate_random_point_target for backward compatibility"""
        return self.generate_random_point_target(center_x, center_y, radius_m)

    def utm_point_to_lonlat(self, utm_point):
        """Alias for target_point_to_source for backward compatibility"""
        return self.target_point_to_source(utm_point)