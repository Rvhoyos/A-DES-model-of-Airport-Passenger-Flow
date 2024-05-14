import simpy
from abc import ABC, abstractmethod


class Gate(ABC):
    """
    Abstract class for an airport gate. Subclasses should implement specific
    behaviors for regional and provincial gates.
    """

    def __init__(self, env, logger, simulation_time):
        """
        Initializes the gate with a simulation environment and a flight schedule.
        """
        self.env = env
        self.current_flight = None  # todo set flight time just like the schedule is set?? prof feedback: simulation...
        # results are correct...?
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
        Abstract method to handle a passenger at the gate. This includes
        checking if the passenger can board the current flight or needs to wait,
        and managing late arrivals and refunds where applicable.
        """
        pass

    def find_current_flight(self, current_time):
        """
        Finds the next flight in the schedule based on the current time.
        :param current_time:
        :return:

        #todo return type from flight schedule
        """
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

    def check_flight_departure(self):
        """
        Checks if the current flight is departing and logs the departure if so.
        :return:
        #todo return type and also fix empty return?
        """
        current_time = self.env.now  # Adjust current_time to be within a 24-hour cycle
        print(f"Checking flight departure at time {current_time}, {self.current_flight.departure_time},")
        departure_time = self.current_flight.departure_time

        if departure_time == 0:
            print(f"Invalid departure time for flight {self.current_flight.flight_number}. Adjusting or skipping...")
            self.current_flight = self.find_current_flight(current_time)
            return
        if departure_time <= current_time:
            print(f"Flight is departing at time {current_time}")  # Debugging print statement
            self.current_flight.departure_log(self.logger)  # Log flight departure
            self.current_flight = self.find_current_flight(current_time)  # Update current_flight to the next flight
