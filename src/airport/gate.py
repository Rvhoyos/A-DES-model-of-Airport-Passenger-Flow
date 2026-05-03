from abc import ABC, abstractmethod


class Gate(ABC):
    """
    Abstract class for an airport gate. Subclasses should implement specific
    behaviors for regional and provincial gates.
    """

    def __init__(self, ctx):
        """
        Initializes the gate with a simulation context and a flight schedule.
        """
        self.ctx = ctx
        self.env = ctx.env
        self.logger = ctx.logger
        self.current_flight = None  # todo set flight time just like the schedule is set?? prof feedback: simulation...
        # results are correct...?

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

    def schedule_departures(self):
        """SimPy process: yields until each flight's departure time, then logs it."""
        for flight in self.flight_schedule:
            delay = flight.departure_time - self.env.now
            if delay > 0:
                yield self.env.timeout(delay)
            flight.departure_log(self.logger)
