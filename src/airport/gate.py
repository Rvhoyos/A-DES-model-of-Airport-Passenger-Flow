import simpy
from abc import ABC, abstractmethod


class Gate(ABC):
    """
    Abstract class for an airport gate. Subclasses should implement specific
    behaviors for regional and provincial gates.
    """

    def __init__(self, env,logger, simulation_time):
        """
        Initializes the gate with a simulation environment and a flight schedule.
        """
        self.env = env
        self.current_flight = None # todo set flight time just like the schedule is set
        self.schedule = self.set_schedule(simulation_time)  # Initialize the flight schedule
        self.logger = logger  # Initialize a logger for the gate

    @abstractmethod
    def set_schedule(self):
        """
        Sets the flight schedule for the gate. This method should be implemented
        by the subclasses to define specific flight timings.
        """
        pass

    @abstractmethod
    def handle_passenger(self, passenger):
        """
        Handles the process of a passenger going through the gate. This includes
        checking if the passenger can board the current flight or needs to wait,
        and managing late arrivals and refunds where applicable.
        """
        pass

    def find_current_flight(self, current_time):
        for flight in self.flight_schedule:
            if flight.departure_time >= current_time:
                self.current_flight = flight
                return flight
        # If no suitable flight is found, return the next flight in the schedule
        if self.flight_schedule:
            next_flight = self.flight_schedule[0]
            self.current_flight = next_flight
            return next_flight
        raise Exception("No suitable flight found in the schedule.")
