import simpy

from .flight import Flight
from .gate import Gate


class ProvincialGate(Gate):
    """
    Represents a gate for provincial flights at an airport.
    Attributes:
        flight_schedule (list): List of Flight objects representing the schedule of flights for the gate.
        gate_name (str): The name of the gate.
        number_of_provincial_gates (int): Class variable to keep track of the number of Provincial gates.
        logger (Logger): Logger instance for event logging.
        env (simpy.Environment): The simulation environment.
    """
    number_of_provincial_gates = 0  # Class variable to keep track of the number of Provincial gates

    def __init__(self, ctx):
        """
        Initializes a provincial gate at an airport.
        :param ctx: SimulationContext (env, logger, simulation_time).
        """
        super().__init__(ctx)
        self.flight_schedule = self.set_schedule(ctx.simulation_time)
        ProvincialGate.number_of_provincial_gates += 1
        self.gate_name = f"Provincial Gate {ProvincialGate.number_of_provincial_gates}"
        self.logger.log_event(0, 'Gate Ready', 0, f'{self.gate_name} initialized',
                              station=self.gate_name)

    def set_schedule(self, simulation_time):
        """
        Generates a flight schedule for the provincial gate.
        :param simulation_time:
        :return:
        """
        num_days = int(simulation_time / 86400)  # Convert simulation time to days
        self.flight_schedule = [Flight('provincial', day * 24 * 60 * 60 + departure_time)
                                for day in range(num_days)
                                for departure_time in range(0, 24 * 60 * 60, 6 * 3600)]
        return self.flight_schedule

    def handle_passenger(self, passenger):
        """
        Handles a provincial passenger at the gate. SimPy generator process:
        yielded via env.process() in Airport.process_passenger().
        :param passenger:
        """
        current_time = self.env.now
        self.logger.log_event(passenger.arrival_time, 'Gate Arrival', self.env.now,
                              f'Arrived at {self.gate_name}',
                              passenger_id=passenger.id, station=self.gate_name)
        current_flight = self.find_current_flight(current_time)
        print(f"Handling provincial passenger at time {self.env.now}")  # Debugging print statement

        if current_flight and current_flight.available_seats[passenger.seat_type] > 0:
            current_flight.board_passenger(passenger)
            print(f"A passenger boards the flight {current_flight} at time {current_time}.")
            self.logger.log_event(passenger.arrival_time, 'Boarding', self.env.now, 'Boarded flight successfully',
                                  passenger_id=passenger.id, station=self.gate_name)

        else:
            print(f"No seats available at time {current_time}.")
            if passenger.arrival_time <= current_flight.departure_time - 90 * 60:
                print(f"A passenger receives a refund at time {current_time} and has left the airport.")
                self.logger.log_event(passenger.arrival_time, 'Refund', self.env.now,
                                      'Received refund and left airport',
                                      passenger_id=passenger.id, station=self.gate_name)
            else:
                print(f"A passenger was late to the airport at{current_flight.departure_time} and left the airport.")
                self.logger.log_event(passenger.arrival_time, 'Late', self.env.now, 'Late to airport and left',
                                      passenger_id=passenger.id, station=self.gate_name)
        yield simpy.Event(self.env).succeed()
