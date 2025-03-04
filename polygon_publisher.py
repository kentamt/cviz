
import math
import numpy as np
import zmq
import time
import json
import random
import math
from publisher import Publisher

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


class KinematicBicycleModel:
    def __init__(self, x=0, y=0, yaw=0, v=0,
                 wheelbase=2.5, lr=1.25, dt=0.1):
        """
        Initialize the kinematic bicycle model.
        :param wheelbase: Distance between front and rear axles (L)
        :param lr: Distance from rear axle to center of mass
        :param dt: Time step for simulation
        """
        self.L = wheelbase
        self.lr = lr
        self.dt = dt
        
        # Initial state (x, y, yaw, velocity)
        self.state = np.array([x, y, yaw, v]) 

    def update(self, acceleration, steering_angle):
        """
        Update the vehicle's state using the kinematic bicycle model.
        :param acceleration: Acceleration input (m/s²)
        :param steering_angle: Steering angle input (radians)
        """
        x, y, theta, v = self.state
        beta = np.arctan((self.lr / self.L) * np.tan(steering_angle))
        
        # Update state using the kinematic equations
        x += v * np.cos(theta + beta) * self.dt
        y += v * np.sin(theta + beta) * self.dt
        theta += (v / self.L) * np.sin(beta) * self.dt
        v += acceleration * self.dt

        # Save new state
        self.state = np.array([x, y, theta, v])

    def get_state(self):
        """Return the current state."""
        return self.state


def main():
    # ZMQ Context
    # context = zmq.Context()
    
    # # Socket to publish messages
    # publisher = context.socket(zmq.PUB)
    # publisher.bind("tcp://127.0.0.1:5555")

    polygon_pub = Publisher(topic_name="polygon", data_type='Polygon')
    message_pub = Publisher(topic_name="message", data_type='Message')

    # Allow socket to settle

    time.sleep(1)
    
    print("🚀 ZMQ Polygon Simulator Started")

    models = []
    model = KinematicBicycleModel(x=300, y=300, v=10)
    acceleration = 0.0 
    steer_ang = math.radians(10.0)

    steering_direction = 1  # 1: right, -1: left. flip every 10 seconds
    total_step = 0
    dt = 1./60.  # [sec]
    try:
        while True:

            # evolve the model
            model.update(acceleration, steer_ang)
            state = model.get_state()
            x, y, yaw, v = state
            
            # send car model
            polygon_data = {
                'points': generate_rectangle(
                    center_x=x,
                    center_y=y,
                    w=10,
                    h=5,
                    yaw=yaw  # [rad]
                )
            }
        
            # message data
            message_data = {
                'message': 'Hello, World!'
            }

            # Publish polygon data
            # publisher.send_json(polygon_data)
            polygon_pub.publish(polygon_data)
            message_pub.publish(message_data)            
            
            # Print for debugging
            print(f"📦 Published Polygon: {len(polygon_data['points'])} points")
            
            # Wait before next polygon
            # time.sleep(random.uniform(0.5, 2))
            time.sleep(dt)
            total_step += 1

            # flip steering direction every 10 seconds
            if total_step % 200 == 0:
                print(f"🔄 Flipping steering direction")
                steering_direction *= -1
                steer_ang = steering_direction * steer_ang  # flip direction
                

    except KeyboardInterrupt:
        print("\n🛑 Simulator stopped")
    finally:
        print("Cleanup")

if __name__ == "__main__":
    main()