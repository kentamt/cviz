import math

import numpy as np
import time
import random
import logging

from publisher import Publisher
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


def main():
    
    # Create publishers
    polygon_pub = Publisher(topic_name="polygon", data_type='Polygon')
    point_pub = Publisher(topic_name="point", data_type='Point2d')
    line_pub = Publisher(topic_name="linestring", data_type='LineString')

    model = KinematicBicycleModel(x=300, y=300, v=20)
    acceleration = 0.0 
    steer_ang = math.radians(10.0)


    time.sleep(1)
    
    print("🚀 ZMQ Geometric Simulator Started")

    try:
        while True:
            
            # evolve the model
            model.update(acceleration, steer_ang)
            state = model.get_state()
            x, y, yaw, v = state
            
            # Publish Polygon
            # polygon_data = {
            #     'points': generate_polygon()
            # }
            
            polygon_data = {
                'points': generate_rectangle(center_x=x, center_y=y, w=10, h=5,yaw=yaw)
            }
            polygon_pub.publish(polygon_data)
            
            # Publish Point
            point_data = {
                'point': generate_point()
            }
            point_pub.publish(point_data)
            
            # Publish LineString
            linestring_data = {
                'points': generate_linestring()
            }
            line_pub.publish(linestring_data)
            
            
            logging.debug(f"Published: Polygon: {polygon_data}, Point: {point_data}, LineString: {linestring_data}")
            
            steer_ang = math.radians(random.uniform(-30, 30))
            
            time.sleep(1./24.)
            # time.sleep(1./10.)
            

    except KeyboardInterrupt:
        print("\n🛑 Simulator stopped")
    finally:
        print("Cleanup")

if __name__ == "__main__":
    main()

    
    
    
    