import numpy as np


class Passenger:
    def __init__(self, gate_type, seat_type,arrival_time):
        self.gate_type = gate_type
        self.seat_type = seat_type
        self.arrival_time = arrival_time
        self.num_bags = self.generate_num_bags()

    def __str__(self):
        return f"Passenger({self.arrival_time}, {self.num_bags}, {self.gate_type}, {self.seat_type})"

    def generate_num_bags(self):
        if self.gate_type == 'commuter':
            # Geometric distribution with p = 60%
            return np.random.geometric(p=0.6) - 1  # Subtracting 1 because geometric distribution starts at 1
        else:
            # Geometric distribution with p = 80% for provincial flights
            return np.random.geometric(p=0.8) - 1  # Subtracting 1 to align with typical bag count
