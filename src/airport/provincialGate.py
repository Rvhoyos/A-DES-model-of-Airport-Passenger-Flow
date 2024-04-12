from flight import Flight
from gate import Gate
from logger import Logger


class ProvincialGate(Gate):
    number_of_provincial_gates = 0  # Class variable to keep track of the number of Provincial gates
    def __init__(self, env, logger, simulation_time):
        super().__init__(env, logger,simulation_time)
        self.flight_schedule = self.set_schedule(simulation_time)  # Generate schedule for 7 days
        ProvincialGate.number_of_provincial_gates += 1
        self.gate_name = f"Regional Gate {ProvincialGate.number_of_provincial_gates}"

    def set_schedule(self, simulation_time):
        num_days = int(simulation_time / 86400)  # Convert simulation time to days
        self.flight_schedule = [Flight('provincial', day * 24 * 60 * 60 + departure_time)
                                for day in range(num_days)
                                for departure_time in range(0, 24 * 60 * 60, 6 * 3600)]
        return self.flight_schedule

    def handle_passenger(self, passenger):
        current_time = self.env.now
        current_flight = self.find_current_flight(current_time)
        self.check_flight_departure()  # Check if the current flight should depart
        print(f"Handling provincial passenger at time {self.env.now}")  # Debugging print statement

        if current_flight and current_flight.available_seats[passenger.seat_type] > 0:
            current_flight.board_passenger(passenger)
            print(f"A passenger boards the flight {current_flight} at time {current_time}.")
            self.logger.log_event(passenger.arrival_time, 'Boarding', self.env.now, 'Boarded flight successfully')

        else:
            # todo logging boarding might be not needed.
            print(f"No seats available at time {current_time}.")
            self.logger.log_event(passenger.arrival_time, 'Boarding', self.env.now, 'No seats available')
            if passenger.arrival_time_at_airport <= current_flight.departure_time - 90 * 60:
                print(f"A passenger receives a refund at time {current_time} and has left the airport.")
                self.logger.log_event(passenger.arrival_time, 'Refund', self.env.now,
                                      'Received refund and left airport')
                yield self.env.timeout(0)  # Ensuring the method yields an event
            else:
                print(f"A passenger was late to the airport at{current_flight.departure_time} and left the airport.")
                self.logger.log_event(passenger.arrival_time, 'Late', self.env.now, 'Late to airport and left')
                yield self.env.timeout(0)  # Ensuring the method yields an event even if no other action is taken
