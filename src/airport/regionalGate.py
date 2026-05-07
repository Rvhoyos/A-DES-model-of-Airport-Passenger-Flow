import simpy

from src.airport.flight import Flight
from src.airport.gate import Gate


class RegionalGate(Gate):
    """
    Gate for regional flights. Regional passengers board if seats are available,
    otherwise they queue (SimPy Store) and board the next flight with open seats.

    Attributes:
        flight_schedule (list): Hourly regional flights starting at 00:30 each day.
        queue (simpy.Store): Overflow queue for passengers when flights are full.
        gate_name (str): Display name for logging.
    """
    number_of_regional_gates = 0  # Class variable to keep track of the number of Regional gates

    def __init__(self, ctx):
        """
        Initializes the regional gate with a simulation context, a flight schedule, and a queue.
        Args:
            ctx (SimulationContext): env, logger, simulation_time.
        """
        super().__init__(ctx)
        self.flight_schedule = self.set_schedule(ctx.simulation_time)
        self.queue = simpy.Store(ctx.env)  # Simpy store to hold passengers in queue
        RegionalGate.number_of_regional_gates += 1
        self.gate_name = f"Regional Gate {RegionalGate.number_of_regional_gates}"
        self.logger.log_event(0, 'Gate Ready', 0, f'{self.gate_name} initialized',
                              station=self.gate_name)

    def set_schedule(self, simulation_time):
        """
        Sets the flight schedule for the regional gate.
        :param simulation_time:
        """
        num_days = int(simulation_time / 86400)  # Convert simulation time to days
        self.flight_schedule = [Flight('regional', day * 24 * 60 * 60 + departure_time)
                                for day in range(num_days)
                                for departure_time in range(30 * 60, 24 * 60 * 60, 60 * 60)]
        return self.flight_schedule

    def handle_passenger(self, passenger):
        """
        Handles a regional passenger at the gate. SimPy generator process:
        yielded via env.process() in Airport.process_passenger().
        :param passenger:
        """
        start_time = self.env.now  # Time when handling starts
        self.logger.log_event(passenger.arrival_time, 'Gate Arrival', self.env.now,
                              f'Arrived at {self.gate_name}',
                              passenger_id=passenger.id, station=self.gate_name)
        current_flight = self.find_current_flight(start_time)

        print(f"Handling regional passenger at time {start_time}")  # Debugging print statement

        if current_flight and current_flight.available_seats['coach'] > 0:
            yield self.env.process(self.board_passenger_queue(passenger)) ## waits until they go through the queue
            if(current_flight.board_passenger(passenger) == True):
                service_time = self.env.now - start_time  # Calculate total service time since arrival to boarding, always returns 0 since boarding is instant.
                print(
                    f"A passenger boards the regional flight departing {current_flight.departure_time}, at time {start_time}. Service Time: {service_time} seconds")
                self.logger.log_event(passenger.arrival_time, 'Boarding', self.env.now,
                                    f'Boarded regional flight successfully. Service Time: {service_time} seconds',
                                    passenger_id=passenger.id, station=self.gate_name,
                                    duration=service_time)
            else:
                print(f"Flight at {current_flight.departure_time} is full. A passenger is queued for next flight.")
                passenger.queue_time = self.env.now
                yield self.queue.put(passenger)
                self.logger.log_event(passenger.arrival_time, 'Queue', self.env.now,
                                    'Queued for next regional flight',
                                    passenger_id=passenger.id, station=self.gate_name)
        else:
            print(f"Flight at {current_flight.departure_time} is full. A passenger is queued for next flight.")
            passenger.queue_time = self.env.now
            yield self.queue.put(passenger)
            self.logger.log_event(passenger.arrival_time, 'Queue', self.env.now,
                                  'Queued for next regional flight',
                                  passenger_id=passenger.id, station=self.gate_name)

    def process_queue(self):
        """
        Process passengers in the queue.
        :return:
        """
        while True:
            if not self.queue.items:
                yield self.env.timeout(1)  # Check the queue again after some time if it's empty
                continue
            current_time = self.env.now
            current_flight = self.find_current_flight(current_time)
            if current_flight and current_flight.available_seats['coach'] > 0:
                passenger = yield self.queue.get()
                waiting_time = self.env.now - passenger.queue_time
                yield self.env.process(self.board_passenger_queue(passenger)) ## waits until they go through the queue
                if(current_flight.board_passenger(passenger) == True):
                    print(
                        f"A queued passenger boards the regional flight departing {current_flight.departure_time}, "
                        f"at time {current_time}. Wait: {waiting_time:.0f}s")
                    self.logger.log_event(passenger.arrival_time, 'Boarding from Queue', self.env.now,
                                          f'Boarded from queue. Wait: {waiting_time:.0f}s',
                                          passenger_id=passenger.id, station=self.gate_name,
                                          duration=waiting_time)
                else:
                    yield self.queue.put(passenger)
            else:
                yield self.env.timeout(1)  # Wait before checking the queue again
