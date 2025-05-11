import math
import time
import random
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from libs.publisher import Publisher
import libs.geojson as geo
from kinematic_model import KinematicBicycleModel

logging.basicConfig(level=logging.INFO)

def main():
    """
    Main simulation loop using GeoJSON with coordinates around London
    """
    # London center coordinates (longitude, latitude)
    LONDON_CENTER_LON_LAT = [-0.1278, 51.5074]
    LONDON_CENTER_X_Y = geo.lonlat_to_utm(LONDON_CENTER_LON_LAT[0], LONDON_CENTER_LON_LAT[1])
    logging.info(f"London center in UTM: {LONDON_CENTER_X_Y} meters")

    # Create publishers for different geometry types
    polygon_pub = Publisher(topic_name="polygon", data_type="GeoJSON")
    multipolygon_pub = Publisher(topic_name="multipolygon", data_type="GeoJSON")
    point_pub = Publisher(topic_name="point", data_type="GeoJSON")
    linestring_pub = Publisher(topic_name="linestring", data_type="GeoJSON")
    multilinestring_pub = Publisher(topic_name="multilinestring", data_type="GeoJSON")
    feature_collection_pub = Publisher(topic_name="feature_collection", data_type="GeoJSON")

    # Define simulation boundaries in UTM coordinates (meters)
    boundary_radius_m = 3000  # 3km radius around London center

    # Calculate UTM boundary coordinates
    x_center, y_center = LONDON_CENTER_X_Y
    x_min = x_center - boundary_radius_m
    x_max = x_center + boundary_radius_m
    y_min = y_center - boundary_radius_m
    y_max = y_center + boundary_radius_m

    # Convert boundary corners to lon/lat for GeoJSON
    sw_corner = geo.utm_to_lonlat(x_min, y_min)
    se_corner = geo.utm_to_lonlat(x_max, y_min)
    ne_corner = geo.utm_to_lonlat(x_max, y_max)
    nw_corner = geo.utm_to_lonlat(x_min, y_max)

    # Set up kinematic models for multiple agents
    num_agents = 20
    acceleration = 0.0
    agent_colors = ["#ff0000", "#00ff00", "#0000ff"]

    # Initialize kinematic models (using UTM coordinates)
    models = []
    for i in range(num_agents):
        # Random position within boundary
        x = random.uniform(x_min, x_max)
        y = random.uniform(y_min, y_max)
        yaw = random.uniform(0, 2 * math.pi)

        # Use appropriate speed for meters (e.g., 10 m/s = 36 km/h)
        models.append(KinematicBicycleModel(x=x, y=y, v=50.0, yaw=yaw))

    # Initialize trajectory storage (in lon/lat for GeoJSON)
    trajectories = [[] for _ in range(num_agents)]

    # Short delay before starting simulation
    time.sleep(1)

    print("🚀 London GeoJSON Simulator Started")
    sim_step = 0

    try:
        while True:
            # Create a feature collection to hold all geometries for this frame
            feature_collection = geo.create_feature_collection([])

            # 1. Create boundary as a LineString Feature
            boundary_coordinates = [
                list(sw_corner),
                list(se_corner),
                list(ne_corner),
                list(nw_corner),
                list(sw_corner)  # Close the boundary
            ]

            boundary_properties = {
                "type": "boundary",
                "color": "#0055ff",
                "lineWidth": 2,
                "description": "Simulation boundary around London"
            }

            boundary_feature = geo.create_linestring_feature(boundary_coordinates, boundary_properties)

            # Publish boundary as separate LineString
            linestring_pub.publish(boundary_feature)

            # Add to feature collection
            feature_collection["features"].append(boundary_feature)

            # 2. Process each agent
            agent_polygons = []

            for i in range(num_agents):
                # Update the model in UTM coordinates
                model = models[i]
                model.update(acceleration, random.uniform(-0.1, 0.1))
                state = model.get_state()
                x, y, yaw, v = state

                # Generate a rectangle for the agent in UTM
                # For a car-sized rectangle (approx. 4.5m x 2m)
                agent_utm_coords = geo.generate_rectangle_coordinates_utm(
                    center_x=x,
                    center_y=y,
                    width_m=20.25,
                    height_m=10.0,
                    yaw=yaw
                )

                # Convert to lon/lat for GeoJSON
                agent_lonlat_coords = geo.utm_rectangle_to_lonlat(agent_utm_coords)

                # Create GeoJSON polygon for this agent
                agent_properties = {
                    "id": f"agent_{i}",
                    "type": "vehicle",
                    "velocity": v,
                    "yaw": yaw,
                    "color": agent_colors[i%len(agent_colors)],
                    "history_limit": 1,
                    "description": f"Vehicle {i} in London"
                }

                agent_feature = geo.create_polygon_feature(agent_lonlat_coords, agent_properties)

                # Add to polygons collection and feature collection
                agent_polygons.append(agent_feature)
                feature_collection["features"].append(agent_feature)

                # Convert current position to lon/lat and add to trajectory
                current_lonlat = geo.utm_to_lonlat(x, y)
                trajectories[i].append(list(current_lonlat))

                # Limit trajectory length
                if len(trajectories[i]) > 50:
                    trajectories[i].pop(0)

                # Create GeoJSON LineString for trajectory (if we have enough points)
                if len(trajectories[i]) > 1:
                    trajectory_properties = {
                        "id": f"trajectory_{i}",
                        "type": "trajectory",
                        "color": "#ffffff",
                        "lineWidth": 2,
                        "description": f"Path of vehicle {i}"
                    }
                    trajectory_feature = geo.create_linestring_feature(trajectories[i], trajectory_properties)
                    feature_collection["features"].append(trajectory_feature)

                # Warp agents if they go outside the boundaries (in UTM coordinates)
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

                # Create a point feature for the agent's center
                center_properties = {
                    "id": f"center_{i}",
                    "type": "center",
                    "color": "#ff0000",
                    "description": f"Center of vehicle {i}"
                }
                center_feature = geo.create_point_feature(list(current_lonlat), center_properties)
                feature_collection["features"].append(center_feature)

            # 3. Create and publish a collection of agent polygons
            agent_collection = geo.create_feature_collection(agent_polygons)
            multipolygon_pub.publish(agent_collection)

            # 4. Generate random observation points (simulating sensor data)
            if sim_step % 3 == 0:  # Only update points every 3 steps
                # Get first vehicle's position in UTM
                if models:
                    vehicle_x, vehicle_y = models[0].state[0], models[0].state[1]
                else:
                    vehicle_x, vehicle_y = x_center, y_center

                # Create points in UTM and convert to lon/lat
                observation_points = []
                for j in range(5):  # Create 5 random observation points
                    # Generate random point in UTM
                    utm_point = geo.generate_random_point_utm(
                        center_x=vehicle_x,
                        center_y=vehicle_y,
                        radius_m=100  # 100m radius
                    )
                    # Convert to lon/lat
                    lonlat_point = geo.utm_point_to_lonlat(utm_point)
                    observation_points.append(list(lonlat_point))

                # Create individual point features for the feature collection
                points_features = []
                for j, point_coords in enumerate(observation_points):
                    point_properties = {
                        "id": f"observation_{j}",
                        "type": "observation",
                        "color": f"#{random.randint(0, 0xFFFFFF):06x}",
                        "history_limit": 50,
                        "description": f"Observation point {j}"
                    }
                    point_feature = geo.create_point_feature(point_coords, point_properties)
                    points_features.append(point_feature)
                    feature_collection["features"].append(point_feature)

                # Also create a MultiPoint feature
                multipoint_properties = {
                    "type": "observations",
                    "count": len(observation_points),
                    "color": "#ffcc00",
                    "history_limit": 1,
                    "description": "Collection of all observation points"
                }
                multipoint_feature = geo.create_multipoint_feature(observation_points, multipoint_properties)

                # Publish both individual points and as a MultiPoint
                point_collection = geo.create_feature_collection(points_features)
                point_pub.publish(point_collection)
                feature_collection["features"].append(multipoint_feature)

            # 5. Publish individual polygon example (first agent)
            if agent_polygons:
                polygon_pub.publish(agent_polygons[0])

            # 6. Publish the combined feature collection
            feature_collection_pub.publish(feature_collection)

            # Logging
            if sim_step % 60 == 0:
                logging.info(f"London simulation step: {sim_step}")

            # Control simulation speed
            time.sleep(1. / 30.)
            sim_step += 1

    except KeyboardInterrupt:
        print("\n🛑 London Simulator stopped")
    finally:
        print("Cleaning up...")

if __name__ == "__main__":
    main()