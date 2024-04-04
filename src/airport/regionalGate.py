import simpy

from src.airport.flight import Flight
from src.airport.gate import Gate


class RegionalGate(Gate):
    def __init__(self, env, logger, simulation_time):
        super().__init__(env, logger, simulation_time)
        self.flight_schedule = self.set_schedule(simulation_time)  # todo round to a day?
        self.queue = simpy.Store(env)

    def set_schedule(self, simulation_time):
        num_days = int(simulation_time / 86400)  # Convert simulation time to days
        self.flight_schedule = [Flight('regional', day * 24 * 60 * 60 + departure_time)
                                for day in range(num_days)
                                for departure_time in range(30 * 60, 24 * 60 * 60, 60 * 60)]
        return self.flight_schedule

    def handle_passenger(self, passenger):
        current_time = self.env.now
        current_flight = self.find_current_flight(current_time)

        if current_flight and current_flight.available_seats['coach'] > 0:
            current_flight.board_passenger(passenger)
            print(
                f"A passenger boards the regional flight departing {current_flight.departure_time}, at time {current_time}.")
        else:
            print(f"Flight at {current_flight.departure_time} is full. A passenger is queued for next flight.")
            passenger.queue_time = current_time
            yield self.queue.put(passenger)

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
            else:
                yield self.env.timeout(1)  # Wait before checking the queue again