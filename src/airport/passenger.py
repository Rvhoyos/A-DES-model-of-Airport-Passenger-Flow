import numpy as np


class Passenger:
    """
    Represents a passenger in the airport simulation.
    """
    ticket_revenue = 0
    passenger_count = 0

    def __init__(self, gate_type, seat_type, arrival_time):
        """
        Initializes a passenger with a gate type, seat type, and arrival time.
        :param gate_type:
        :param seat_type:
        :param arrival_time:
        """
        self.gate_type = gate_type
        self.seat_type = seat_type
        self.arrival_time = arrival_time
        self.num_bags = self.generate_num_bags()
        self.cost = self.calculate_cost()  # Calculate the cost of the ticket for this passenger
        Passenger.ticket_revenue += self.cost
        Passenger.passenger_count += 1

    def generate_num_bags(self):
        """
        Generates the number of bags for the passenger based on the gate type.
        :return: random number representing amount of bags for current passenger.
        """
        if self.gate_type == 'commuter':
            # Geometric distribution with p = 60%
            return np.random.geometric(p=0.6) - 1  # Subtracting 1 because geometric distribution starts at 1
        else:
            # Geometric distribution with p = 80% for provincial flights
            return np.random.geometric(p=0.8) - 1  # Subtracting 1 to align with typical bag count

    def calculate_cost(self):
        """
        Calculates the cost of the ticket for the passenger based on the seat and gate type.
        :return:
        """
        if self.seat_type == 'business':
            return 1000
        elif self.gate_type == 'provincial':
            return 500
        else:  # Commuter flight
            return 200

    def __str__(self):
        """
        String representation of the passenger.
        :return:
        """
        return f"Passenger({self.arrival_time}, {self.num_bags}, {self.gate_type}, {self.seat_type})"
