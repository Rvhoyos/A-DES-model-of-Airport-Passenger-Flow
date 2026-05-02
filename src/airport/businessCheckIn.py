from .checkinCounter import CheckinCounter


class BusinessClassCounter(CheckinCounter):
    """
        Represents a business class check-in counter at an airport.

        Attributes:
            number_of_agents
            env (simpy.Environment): The simulation environment.
            logger (Logger): Logger instance for event logging.
    """
    number_of_agents = 0  # Static variable to keep track of the number of business class counters

    def __init__(self, ctx):
        """
        Initializes a business class check-in counter object.
        :param ctx: SimulationContext (env, logger, simulation_time).
        """
        super().__init__(ctx)
        BusinessClassCounter.number_of_agents += 1
        self.counter_type = "Business Class"
        self.station_name = f"Business Counter {BusinessClassCounter.number_of_agents}"

    def handle_check_in(self, passenger):
        """
              Handle the check-in process for a business class passenger.

              Args:
                  passenger (Passenger): The passenger to check in.
              """
        with self.counter.request() as req:
            self.logger.log_event(passenger.arrival_time, 'Check-in Queue', self.env.now,
                                  'Entered business check-in queue',
                                  passenger_id=passenger.id, gate_type=passenger.gate_type,
                                  seat_type=passenger.seat_type, station=self.station_name)
            yield req
            self.logger.log_event(passenger.arrival_time, 'Check-in Start', self.env.now,
                                  'Started business check-in service',
                                  passenger_id=passenger.id, gate_type=passenger.gate_type,
                                  seat_type=passenger.seat_type, station=self.station_name)
            boarding_pass_time = self.print_boarding_pass()
            bag_check_time = self.check_bags(passenger)
            problem_delay_time = self.handle_problems_and_delays()
            total_time = boarding_pass_time + bag_check_time + problem_delay_time
            print(f"Business passenger {passenger.arrival_time} is at the counter.")
            yield self.env.timeout(total_time)  # Use SimPy's timeout for service time
            self.logger.log_event(passenger.arrival_time, 'Check-in', self.env.now, f'B. service time:{total_time}',
                                  passenger_id=passenger.id, gate_type=passenger.gate_type,
                                  seat_type=passenger.seat_type, station=self.station_name,
                                  duration=total_time)
