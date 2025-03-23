import math
import time
import random
import logging
import json

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from libs.publisher import Publisher
from kinematic_model import KinematicBicycleModel

logging.basicConfig(level=logging.INFO)


def generate_rectangle_coordinates(center_x, center_y, w, h, yaw=0):
    """Generate a rectangle polygon with specified parameters in GeoJSON format."""
    points = [
        [
            center_x + w * math.cos(yaw) - h * math.sin(yaw),
            center_y + w * math.sin(yaw) + h * math.cos(yaw)
        ],
        [
            center_x - w * math.cos(yaw) - h * math.sin(yaw),
            center_y - w * math.sin(yaw) + h * math.cos(yaw)
        ],
        [
            center_x - w * math.cos(yaw) + h * math.sin(yaw),
            center_y - w * math.sin(yaw) - h * math.cos(yaw)
        ],
        [
            center_x + w * math.cos(yaw) + h * math.sin(yaw),
            center_y + w * math.sin(yaw) - h * math.cos(yaw)
        ],
        [
            center_x + w * math.cos(yaw) - h * math.sin(yaw),
            center_y + w * math.sin(yaw) + h * math.cos(yaw)
        ]  # Close the polygon
    ]

    return points


def generate_random_point(center_x, center_y, radius=30):
    """Generate a random point near a center with specified radius in GeoJSON format."""
    angle = random.uniform(0, 2 * math.pi)
    distance = random.uniform(0, radius)

    return [
        center_x + distance * math.cos(angle),
        center_y + distance * math.sin(angle)
    ]


def create_point_feature(coordinates, properties=None):
    """Create a GeoJSON Point feature"""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": coordinates
        },
        "properties": properties or {}
    }


def create_linestring_feature(coordinates, properties=None):
    """Create a GeoJSON LineString feature"""
    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coordinates
        },
        "properties": properties or {}
    }


def create_polygon_feature(coordinates, properties=None):
    """Create a GeoJSON Polygon feature"""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [coordinates]  # Note: GeoJSON Polygons use an array of linear rings
        },
        "properties": properties or {}
    }


def create_multipoint_feature(coordinates, properties=None):
    """Create a GeoJSON MultiPoint feature"""
    return {
        "type": "Feature",
        "geometry": {
            "type": "MultiPoint",
            "coordinates": coordinates
        },
        "properties": properties or {}
    }


def create_feature_collection(features):
    """Create a GeoJSON FeatureCollection"""
    return {
        "type": "FeatureCollection",
        "features": features
    }


def main():
    """
    Main simulation loop using GeoJSON format for all geometries
    """
    # Create publishers for different geometry types
    polygon_pub = Publisher(topic_name="polygon", data_type="GeoJSON")
    multipolygon_pub = Publisher(topic_name="multipolygon", data_type="GeoJSON")
    point_pub = Publisher(topic_name="point", data_type="GeoJSON")
    linestring_pub = Publisher(topic_name="linestring", data_type="GeoJSON")
    multilinestring_pub = Publisher(topic_name="multilinestring", data_type="GeoJSON")
    feature_collection_pub = Publisher(topic_name="feature_collection", data_type="GeoJSON")


    # Set up kinematic models for multiple agents
    num_agents = 3
    acceleration = 0.0
    x_min, x_max, y_min, y_max = -500, 500, -500, 500
    agent_colors = ["#ff0000", "#00ff00", "#0000ff"]

    # Initialize kinematic models
    models = []
    for i in range(num_agents):
        x = random.uniform(x_min, x_max)
        y = random.uniform(y_min, y_max)
        yaw = random.uniform(0, 2 * math.pi)
        models.append(KinematicBicycleModel(x=x, y=y, v=30, yaw=yaw))

    # Initialize state
    trajectories = [[] for _ in range(num_agents)]
    time.sleep(1)  # Small delay before starting simulation

    print("🚀 GeoJSON Simulator Started")
    sim_step = 0

    try:
        while True:
            # Create a feature collection to hold all geometries for this frame
            feature_collection = create_feature_collection([])

            # 1. Create boundary as a LineString Feature
            boundary_coordinates = [
                [x_min, y_min],
                [x_max, y_min],
                [x_max, y_max],
                [x_min, y_max],
                [x_min, y_min]  # Close the boundary
            ]

            boundary_properties = {
                "type": "boundary",
                "color": "#0055ff",
                "lineWidth": 2
            }

            boundary_feature = create_linestring_feature(boundary_coordinates, boundary_properties)

            # Publish boundary as separate LineString
            linestring_pub.publish(boundary_feature)

            # Add to feature collection
            feature_collection["features"].append(boundary_feature)

            # 2. Process each agent
            agent_polygons = []

            for i in range(num_agents):
                # Update the model
                model = models[i]
                model.update(acceleration, random.uniform(-0.3, 0.3))
                state = model.get_state()
                x, y, yaw, v = state

                # Generate a rectangle polygon for the agent
                agent_coordinates = generate_rectangle_coordinates(x, y, w=15, h=10, yaw=yaw)

                # Create GeoJSON polygon for this agent
                agent_properties = {
                    "id": f"agent_{i}",
                    "type": "vehicle",
                    "velocity": v,
                    "yaw": yaw,
                    "color": agent_colors[i],
                    'history_limit': 1
                }

                agent_feature = create_polygon_feature(agent_coordinates, agent_properties)

                # Add to polygons collection and feature collection
                agent_polygons.append(agent_feature)
                feature_collection["features"].append(agent_feature)

                # Add current position to the trajectory
                trajectories[i].append([x, y])

                # Limit trajectory length
                if len(trajectories[i]) > 50:
                    trajectories[i].pop(0)

                # Create GeoJSON LineString for trajectory (if we have enough points)
                if len(trajectories[i]) > 1:
                    trajectory_properties = {
                        "id": f"trajectory_{i}",
                        "type": "trajectory",
                        "color": "#333333",
                        "lineWidth": 2
                    }
                    trajectory_feature = create_linestring_feature(trajectories[i], trajectory_properties)
                    feature_collection["features"].append(trajectory_feature)

                # Warp agents if they go outside the boundaries
                if x > x_max:
                    models[i].state[0] = x_min
                    trajectories[i] = []
                if y > y_max:
                    models[i].state[1] = y_min
                    trajectories[i] = []
                if x < x_min:
                    models[i].state[0] = x_max
                    trajectories[i] = []
                if y < y_min:
                    models[i].state[1] = y_max
                    trajectories[i] = []

                # Create a point for the agent's center
                center_properties = {
                    "id": f"center_{i}",
                    "type": "center",
                    "color": "#ff0000"
                }
                center_feature = create_point_feature([x, y], center_properties)
                feature_collection["features"].append(center_feature)

            # 3. Create and publish a collection of agent polygons as a MultiPolygon
            # Use a FeatureCollection instead for more attributes
            agent_collection = create_feature_collection(agent_polygons)
            multipolygon_pub.publish(agent_collection)

            # 4. Generate random observation points (simulating sensor data)
            if sim_step % 3 == 0:  # Only update points every 10 steps
                # Create points as a MultiPoint feature
                observation_points = []
                for j in range(5):  # Create 5 random observation points
                    observation_points.append(generate_random_point(
                        center_x=models[0].state[0],
                        center_y=models[0].state[1],
                        radius=100
                    ))

                # Create individual point features for the feature collection
                points_features = []
                for j, point_coords in enumerate(observation_points):
                    point_properties = {
                        "id": f"observation_{j}",
                        "type": "observation",
                        "color": f"#{random.randint(0, 0xFFFFFF):06x}",
                        "history_limit": 500
                    }
                    point_feature = create_point_feature(point_coords, point_properties)
                    points_features.append(point_feature)
                    feature_collection["features"].append(point_feature)

                # Also create a MultiPoint feature
                multipoint_properties = {
                    "type": "observations",
                    "count": len(observation_points),
                    "color": "#ffcc00",
                    "history_limit": "1"
                }
                multipoint_feature = create_multipoint_feature(observation_points, multipoint_properties)

                # Publish both individual points and as a MultiPoint
                point_collection = create_feature_collection(points_features)
                point_pub.publish(point_collection)
                feature_collection["features"].append(multipoint_feature)

            # 5. Publish individual polygon example (first agent)
            if agent_polygons:
                polygon_pub.publish(agent_polygons[0])

            # 6. Publish the combined feature collection
            feature_collection_pub.publish(feature_collection)

            # Logging
            if sim_step % 60 == 0:
                logging.info(f"Simulation step: {sim_step}")

            # Control simulation speed
            time.sleep(1. / 30.)
            sim_step += 1

    except KeyboardInterrupt:
        print("\n🛑 Simulator stopped")
    finally:
        print("Cleaning up...")


if __name__ == "__main__":
    main()