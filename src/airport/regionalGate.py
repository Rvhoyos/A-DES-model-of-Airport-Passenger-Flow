import simpy

from src.airport.flight import Flight
from src.airport.gate import Gate

"""
Abstract base class for an airport gate. Subclasses should implement specific
behaviors for regional and provincial gates.

Attributes:
    env (simpy.Environment): The simulation environment.
    current_flight (Flight): The current flight at the gate.
    schedule (list): The schedule of flights at the gate.
    logger (Logger): Logger instance for event logging.
"""


class RegionalGate(Gate):
    number_of_regional_gates = 0  # Class variable to keep track of the number of Regional gates
    """
    Represents a regional gate at an airport. Inherits from the Gate class.

    Attributes:
        queue (simpy.Store): Queue of passengers waiting for the next flight.
    """
    def __init__(self, env, logger, simulation_time):
        """
        Initializes the regional gate with a simulation environment, a flight schedule, and a queue.

        Args:
            env (simpy.Environment): The simulation environment.
            logger (Logger): Logger instance for event logging.
            simulation_time (int): Total simulation time in seconds.
        """
        super().__init__(env, logger, simulation_time)
        self.flight_schedule = self.set_schedule(simulation_time)
        self.queue = simpy.Store(env) # Simpy store to hold passengers in queue
        RegionalGate.number_of_regional_gates += 1
        self.gate_name = f"Regional Gate {RegionalGate.number_of_regional_gates}"


    def set_schedule(self, simulation_time):
        num_days = int(simulation_time / 86400)  # Convert simulation time to days
        self.flight_schedule = [Flight('regional', day * 24 * 60 * 60 + departure_time)
                                for day in range(num_days)
                                for departure_time in range(30 * 60, 24 * 60 * 60, 60 * 60)]
        return self.flight_schedule

    def handle_passenger(self, passenger):
        start_time = self.env.now  # Time when handling starts
        current_flight = self.find_current_flight(start_time)
        self.check_flight_departure()  # Check if the current flight should depart

        print(f"Handling regional passenger at time {start_time}")  # Debugging print statement

        if current_flight and current_flight.available_seats['coach'] > 0:
            current_flight.board_passenger(passenger)
            service_time = self.env.now - start_time  # Calculate total service time since arrival to boarding
            print(
                f"A passenger boards the regional flight departing {current_flight.departure_time}, at time {start_time}. Service Time: {service_time} seconds")
            self.logger.log_event(passenger.arrival_time, 'Boarding', self.env.now,
                                  f'Boarded regional flight successfully. Service Time: {service_time} seconds')
        else:
            # todo Queue never gets used, Number of flights are DRASTICALLY bigger then number of passengers.... should not be the case.
            # Last output was:
            #   Toal Number of Passengers: 259
            #   Total number of flights: 336
            print(f"Flight at {current_flight.departure_time} is full. A passenger is queued for next flight.")
            passenger.queue_time = self.env.now
            yield self.queue.put(passenger)  # Wait until the passenger is processed from the queue
            waiting_time = start_time - passenger.queue_time  # Calculate waiting time
            print(
                f"Passenger {passenger.arrival_time} was queued and waited {waiting_time} seconds,before boarding.")
            self.logger.log_event(passenger.arrival_time, 'Queue', self.env.now,
                                  f'Passenger queued for next regional flight. Waiting Time: {waiting_time} seconds')

    def process_queue(self):
        while True:
            # ("Starting queue processing")
            if not self.queue.items:
                yield self.env.timeout(1)  # Check the queue again after some time if it's empty
                continue

            current_time = self.env.now
            current_flight = self.find_current_flight(current_time)

            if current_flight and current_flight.available_seats['coach'] > 0:
                passenger = yield self.queue.get()
                current_flight.board_passenger(passenger)
                print(
                    f"A queued passenger boards the regional flight departing {current_flight.departure_time}, at time {current_time}.")
                self.logger.log_event(passenger.arrival_time, 'Boarding from Queue', self.env.now,
                                      'Boarded regional flight from queue')
            else:
                yield self.env.timeout(1)  # Wait before checking the queue again
