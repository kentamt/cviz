import math

import numpy as np
import time
import random
import logging


import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from libs.publisher import Publisher
from kinematic_model import KinematicBicycleModel

logging.basicConfig(level=logging.DEBUG)


def generate_rectangle(center_x=300, center_y=300, w=100, h=100, yaw=0):
    """Generate a rectangle polygon with specified parameters."""
    points = [
        {
            'x': center_x + w * math.cos(yaw) - h * math.sin(yaw),
            'y': center_y + w * math.sin(yaw) + h * math.cos(yaw)
        },
        {
            'x': center_x - w * math.cos(yaw) - h * math.sin(yaw),
            'y': center_y - w * math.sin(yaw) + h * math.cos(yaw)
        },
        {
            'x': center_x - w * math.cos(yaw) + h * math.sin(yaw),
            'y': center_y - w * math.sin(yaw) - h * math.cos(yaw)
        },
        {
            'x': center_x + w * math.cos(yaw) + h * math.sin(yaw),
            'y': center_y + w * math.sin(yaw) - h * math.cos(yaw)
        }
    ]
    
    return points

def generate_polygon(num_points=5, center_x=300, center_y=300, radius=100):
    """Generate a random polygon with specified parameters."""
    angles = [random.uniform(0, 2 * math.pi) for _ in range(num_points)]
    angles.sort()
    
    points = [
        {
            'x': center_x + radius * math.cos(angle),
            'y': center_y + radius * math.sin(angle)
        }
        for angle in angles
    ]
    
    return points

def generate_point(center_x=300, center_y=300, radius=30):
    """Generate a random point near a center with specified radius."""
    angle = random.uniform(0, 2 * math.pi)
    distance = random.uniform(0, radius)
    
    return {
        'x': center_x + distance * math.cos(angle),
        'y': center_y + distance * math.sin(angle)
    }

def generate_linestring(num_points=5, center_x=300, center_y=300, radius=100):
    """Generate a random linestring with specified parameters."""
    points = []
    current_x, current_y = center_x, center_y
    
    for _ in range(num_points):
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(0, radius)
        
        current_x += distance * math.cos(angle)
        current_y += distance * math.sin(angle)
        
        points.append({
            'x': current_x,
            'y': current_y
        })
    
    return points


# simulator main
def main():
    
    # Create publishers
    polygon_pub_1 = Publisher(topic_name="polygon_1", data_type='Polygon')
    polygon_pub_2 = Publisher(topic_name="polygon_2", data_type='Polygon')
    point_pub = Publisher(topic_name="point", data_type='Point2d')
    line_pub_1 = Publisher(topic_name="linestring_1", data_type='LineString')
    line_pub_2 = Publisher(topic_name="linestring_2", data_type='LineString')
    text_pub_1 = Publisher(topic_name="text_1", data_type='Text')
    text_pub_2 = Publisher(topic_name="text_2", data_type='Text')

    model_1 = KinematicBicycleModel(x=400, y=100, v=30)
    model_2 = KinematicBicycleModel(x=600, y=500, v=10, yaw=math.radians(125))
    acceleration = 0.0 

    time.sleep(1)
    
    print("🚀 Geometric Simulator Started")
    sim_step = 0
    trajectory_1, trajectory_2 = [], []
    try:
        while True:

            # evolve the model
            steer_ang = math.radians(2.0)
            model_1.update(acceleration, steer_ang)
            state = model_1.get_state()
            x1, y1, yaw1, v1 = state
            polygon_data_1 = {            
                'points': generate_rectangle(center_x=x1, center_y=y1, w=10, h=5,yaw=yaw1)
            }

            steer_ang = math.radians(-2.5)
            model_2.update(acceleration, steer_ang)
            state = model_2.get_state()
            x2, y2, yaw2, v2 = state
            polygon_data_2 = {
                'points': generate_rectangle(center_x=x2, center_y=y2, w=20, h=10,yaw=yaw2)
            }

            point_data = {
                'point': generate_point(center_x=x1, center_y=y1)
            }

            text_data_1 = {
                'text': f"v1: {sim_step}: yaw: {yaw1:0.2f}, v: {v1}",
                'position': {'x': x1+10, 'y': y1+10}
            }
            text_data_2 = {
                'text': f"v2: {sim_step}: yaw: {yaw2:0.2f}, v: {v2}",
                'position': {'x': x2+10, 'y': y2+10}
            }

            # push the car's trajectory
            trajectory_1.append({'x': float(x1), 'y': float(y1)})
            if len(trajectory_1) > 100:
                trajectory_1.pop(0)
            linestring_data_1 = {'points': trajectory_1}

            trajectory_2.append({'x': float(x2), 'y': float(y2)})
            if len(trajectory_2) > 100:
                trajectory_2.pop(0)
            linestring_data_2 = {'points': trajectory_2}

            # Publish data for visualisation        
            polygon_pub_1.publish(polygon_data_1)
            polygon_pub_2.publish(polygon_data_2)
            point_pub.publish(point_data)
            line_pub_1.publish(linestring_data_1)
            line_pub_2.publish(linestring_data_2)
            text_pub_1.publish(text_data_1)
            text_pub_2.publish(text_data_2)
            
            # logging.debug(f"Published: Polygon: {polygon_data}")
            # logging.debug(f"Published: Point: {point_data}")
            # logging.debug(f"Published: LineString: {linestring_data}")
            logging.debug(f"Published: Text: {text_data_1}")
            
            time.sleep(1./60.)
            sim_step += 1
            
    except KeyboardInterrupt:
        print("\n🛑 Simulator stopped")
    finally:
        print("Cleanup")

if __name__ == "__main__":
    main()

    
    
    
    