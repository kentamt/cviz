import logging
import random
import time
from collections import deque

import networkx as nx
import osmnx as ox
from pyproj import Transformer
from shapely.geometry import LineString

from libs.publisher import Publisher
import libs.geojson as geo

LONDON_CENTER = (51.5074, -0.1278)
DOWNLOAD_DISTANCE_M = 3500  # roughly the same area as the existing London example
NUM_AGENTS = 35
HISTORY_LENGTH = 60
UPDATE_DT = 0.01  # seconds
SIM_DT = 1.0  # seconds
SPEED_RANGE_MPS = (4.0, 14.0)
COLOR_CYCLE = ["#ff6b6b", "#4ecdc4", "#ffe66d", "#1a9df4", "#c56cf0"]

logging.basicConfig(level=logging.INFO)


def load_graph():
    logging.info("Fetching OSM drive network around London (this may take a moment)...")
    graph = ox.graph_from_point(
        LONDON_CENTER,
        dist=DOWNLOAD_DISTANCE_M,
        network_type="drive",
        simplify=True
    )
    logging.info("Projecting graph to metric CRS...")
    graph = ox.project_graph(graph)
    return graph


def build_transformer(graph):
    crs = graph.graph.get("crs")
    if not crs:
        raise RuntimeError("Graph CRS missing; cannot transform back to WGS84")
    return Transformer.from_crs(crs, "EPSG:4326", always_xy=True)


class RoadAgent:
    def __init__(self, graph, transformer, node_ids, agent_id):
        self.graph = graph
        self.transformer = transformer
        self.node_ids = node_ids
        self.id = agent_id
        self.history = deque(maxlen=HISTORY_LENGTH)
        self.speed_mps = random.uniform(*SPEED_RANGE_MPS)
        self.color = COLOR_CYCLE[agent_id % len(COLOR_CYCLE)]
        self.path = []
        self.segment_index = 0
        self.distance_on_edge = 0.0
        self.current_lonlat = None
        self._reset_path()

    def _reset_path(self, start=None):
        self.path = self._generate_path(start)
        self.segment_index = 0
        self.distance_on_edge = 0.0
        self.speed_mps = random.uniform(*SPEED_RANGE_MPS)
        self._update_position()
        if self.current_lonlat:
            self.history.append(self.current_lonlat)

    def _generate_path(self, start=None):
        attempts = 0
        while attempts < 20:
            origin = start if start is not None else random.choice(self.node_ids)
            destination = random.choice(self.node_ids)
            if origin == destination:
                attempts += 1
                continue
            try:
                path = nx.shortest_path(self.graph, origin, destination, weight="length")
                if len(path) >= 2:
                    return path
            except nx.NetworkXNoPath:
                pass
            attempts += 1
        logging.warning("Falling back to a simple edge path")
        origin = start if start is not None else random.choice(self.node_ids)
        neighbors = list(self.graph.neighbors(origin))
        if not neighbors:
            origin = random.choice(self.node_ids)
            neighbors = list(self.graph.neighbors(origin))
        if not neighbors:
            raise RuntimeError("Unable to find any neighboring nodes in graph")
        return [origin, random.choice(neighbors)]

    def _edge_data(self, u, v):
        data = self.graph.get_edge_data(u, v)
        if not data:
            data = self.graph.get_edge_data(v, u)
        if not data:
            raise RuntimeError(f"No edge data between {u} and {v}")
        first_key = next(iter(data))
        return data[first_key]

    def _edge_geometry(self, u, v, data):
        if data.get("geometry"):
            coords = list(data["geometry"].coords)
        else:
            coords = [
                (self.graph.nodes[u]["x"], self.graph.nodes[u]["y"]),
                (self.graph.nodes[v]["x"], self.graph.nodes[v]["y"])
            ]
        return LineString(coords)

    def _update_position(self):
        u = self.path[self.segment_index]
        v = self.path[self.segment_index + 1]
        data = self._edge_data(u, v)
        line = self._edge_geometry(u, v, data)
        target_distance = min(self.distance_on_edge, line.length)
        point_xy = line.interpolate(target_distance)
        lon, lat = self.transformer.transform(point_xy.x, point_xy.y)
        self.current_lonlat = [lon, lat]
        self.history.append(self.current_lonlat)

    def advance(self, dt):
        distance_to_cover = self.speed_mps * dt
        while distance_to_cover > 0 and self.segment_index < len(self.path) - 1:
            u = self.path[self.segment_index]
            v = self.path[self.segment_index + 1]
            data = self._edge_data(u, v)
            edge_length = data.get("length")
            if edge_length is None:
                line = self._edge_geometry(u, v, data)
                edge_length = line.length
            remaining = edge_length - self.distance_on_edge
            if distance_to_cover < remaining:
                self.distance_on_edge += distance_to_cover
                distance_to_cover = 0
            else:
                distance_to_cover -= remaining
                self.segment_index += 1
                if self.segment_index >= len(self.path) - 1:
                    self._reset_path(start=self.path[-1])
                    return
                self.distance_on_edge = 0.0
        self._update_position()

    def point_feature(self):
        if not self.current_lonlat:
            return None
        properties = {
            "id": f"road_agent_{self.id}",
            "type": "vehicle",
            "color": self.color,
            "speed_mps": round(self.speed_mps, 2),
            "history_limit": 1
        }
        return geo.create_point_feature(self.current_lonlat, properties)

    def trail_feature(self):
        if len(self.history) < 2:
            return None
        properties = {
            "id": f"road_trail_{self.id}",
            "type": "trajectory",
            "color": self.color,
            "history_limit": HISTORY_LENGTH
        }
        return geo.create_linestring_feature(list(self.history), properties)


def main():
    graph = load_graph()
    transformer = build_transformer(graph)
    node_ids = list(graph.nodes)

    agents = [
        RoadAgent(graph, transformer, node_ids, agent_id=i)
        for i in range(NUM_AGENTS)
    ]

    point_pub = Publisher(topic_name="point", data_type="GeoJSON")
    trail_pub = Publisher(topic_name="linestring", data_type="GeoJSON")

    logging.info("Starting OSM road network simulation")

    try:
        while True:
            point_features = []
            trail_features = []

            for agent in agents:
                agent.advance(SIM_DT)
                point_feature = agent.point_feature()
                if point_feature:
                    point_features.append(point_feature)
                trail_feature = agent.trail_feature()
                if trail_feature:
                    trail_features.append(trail_feature)

            if point_features:
                point_pub.publish(geo.create_feature_collection(point_features))
            if trail_features:
                trail_pub.publish(geo.create_feature_collection(trail_features))

            time.sleep(UPDATE_DT)

    except KeyboardInterrupt:
        logging.info("Stopping OSM road network simulation")


if __name__ == "__main__":
    main()
