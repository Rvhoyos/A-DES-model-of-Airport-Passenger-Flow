from pandas.io import parsers
from abc import ABC, abstractmethod
import simpy
from .RVG.randomNumberGenerator import ExponentialRandomNumberGenerator

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
        self.current_flight = None 
        self.boarding_bridge = simpy.PriorityResource(self.env, capacity=1)

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
   
    def board_passenger_queue(self, passenger):
        ## Simpy resource that handles passenger boarding / walking the bridge
        ## Use resource priortiy to give provincial business class first access before coach passengers.
        ## Priority based on seat type
        if(passenger.seat_type == "business"):
            priority = 0
        else:
            priority = 1

        request = self.boarding_bridge.request(priority=priority)
        yield request ## wait until request is granted
        ## once granted, generate a service time based on bags (30 seconds per bag)
        if(passenger.num_bags !=0):
            service_time = passenger.num_bags*ExponentialRandomNumberGenerator(30).generate()
        else:
            service_time = ExponentialRandomNumberGenerator(1/30).generate()
        yield self.env.timeout(service_time)
        self.boarding_bridge.release(request)
        ## releases the resouce since passenger has been serviced. 

