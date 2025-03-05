import numpy as np

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