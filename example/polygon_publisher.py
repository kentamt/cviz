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
    polygon_pub = Publisher(topic_name="polygon", data_type='Polygon')
    point_pub = Publisher(topic_name="point", data_type='Point2d')
    line_pub = Publisher(topic_name="linestring", data_type='LineString')

    model = KinematicBicycleModel(x=400, y=100, v=100)
    acceleration = 0.0 
    steer_ang = math.radians(0.0)

    time.sleep(1)
    
    print("🚀 Geometric Simulator Started")
    sim_step = 0
    trajectory = []
    try:
        while True:

            # evolve the model
            steer_ang = math.radians(2.0 * math.sin(0.1 * sim_step)**2)
            acceleration = random.uniform(-1, 1)
            model.update(acceleration, steer_ang)
            state = model.get_state()
            x, y, yaw, v = state

            # Generate data for visualisation    
            polygon_data = {
                'points': generate_rectangle(center_x=x, center_y=y, w=10, h=5,yaw=yaw)
            }

            point_data = {
                'point': generate_point(center_x=x, center_y=y)
            }

            # push the car's trajectory
            trajectory.append({'x': float(x), 'y': float(y)})
            if len(trajectory) > 100:
                trajectory.pop(0)
            linestring_data = {'points': trajectory}

            # Publish data for visualisation        
            polygon_pub.publish(polygon_data)
            point_pub.publish(point_data)
            line_pub.publish(linestring_data)
            
            logging.debug(f"Published: Polygon: {polygon_data}")
            logging.debug(f"Published: Point: {point_data}")
            # logging.debug(f"Published: LineString: {linestring_data}")
            
            time.sleep(1./60.)
            sim_step += 1
            
    except KeyboardInterrupt:
        print("\n🛑 Simulator stopped")
    finally:
        print("Cleanup")

if __name__ == "__main__":
    main()

    
    
    
    