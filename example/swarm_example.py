import math

import numpy as np
import time
import random
import logging


import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from libs.publisher import Publisher
from kinematic_model import KinematicBicycleModel

logging.basicConfig(level=logging.INFO)


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


def generate_point(center_x=300, center_y=300, radius=30):
    """Generate a random point near a center with specified radius."""
    angle = random.uniform(0, 2 * math.pi)
    distance = random.uniform(0, radius)
    
    return {
        'x': center_x + distance * math.cos(angle),
        'y': center_y + distance * math.sin(angle)
    }



# simulator main
def main():
    """
    PolygonVector:
    {
        'polygons': [
            {
                'points': [
                    {'x': 100, 'y': 100}, 
                    {'x': 200, 'y': 100},
                    {'x': 200, 'y': 200},
                    {'x': 100, 'y': 200}
                ]
            },
            {
                'points': [
                    {'x': 300, 'y': 300},
                    {'x': 400, 'y': 300},
                    {'x': 400, 'y': 400},
                    {'x': 300, 'y': 400}
                ]
            }
        ] 
    }
    """    
    polygon_vector_pub = Publisher(topic_name="polygon_vector", data_type='PolygonVector')
    linestring_pub = Publisher(topic_name="boundary", data_type='LineString')
    
    num_agents = 100
    acceleration = 0.0 
    x_min, x_max, y_min, y_max = -1000, 1000, -1000, 1000
    models = []
    for i in range(num_agents):
        x = random.uniform(x_min, x_max)
        y = random.uniform(y_min, y_max)
        yaw = random.uniform(0, 2 * math.pi)
        models.append(KinematicBicycleModel(x=x, y=y, v=10, yaw=yaw))

    # boundary data
    boundary_data = {
        'points': [
            {'x': x_min, 'y': y_min},
            {'x': x_max, 'y': y_min},
            {'x': x_max, 'y': y_max},
            {'x': x_min, 'y': y_max},
            {'x': x_min, 'y': y_min}
        ]
    }
    boundary_data['life_time'] = 0
    boundary_data['history_limit'] = 1
    boundary_data['color'] = '0x0055ff'
    
    log_interval = 60
        
    sim_step = 0
    try:
        while True:

            polygons = []

            # evolve the model
            for i in range(num_agents):

                # update the model
                model = models[i]
                model.update(acceleration, random.uniform(-0.2, 0.2))
                state = model.get_state()
                x, y, yaw, v = state

                # generate a rectangle polygon
                polygon_data = {
                    'points': generate_rectangle(x, y, w=5, h=2.5, yaw=yaw)
                }
                polygons.append(polygon_data)

                # warp agents                       
                if x > x_max:
                    models[i].state[0] = x_min
                if y > y_max:
                    models[i].state[1] = y_min
                if x < x_min:
                    models[i].state[0] = x_max
                if y < y_min:
                    models[i].state[1] = y_max

            # polygon vector data                             
            polygon_vector_data = {'polygons': polygons}                 
            polygon_vector_data['life_time'] = 0
            polygon_vector_data['history_limit'] = 1
            polygon_vector_data['color'] = '0x00ffff'

            polygon_vector_pub.publish(polygon_vector_data)
            linestring_pub.publish(boundary_data)    

            if sim_step % log_interval == 0:
                logging.info(f"Step: {sim_step}")

            time.sleep(1./60.)
            sim_step += 1
            
    except KeyboardInterrupt:
        print("\n🛑 Simulator stopped")
    finally:
        print("Cleanup")

if __name__ == "__main__":
    main()

    
    
    
    