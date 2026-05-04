from .checkinCounter import CheckinCounter


class CoachCounter(CheckinCounter):
    """
        Represents a coach class check-in counter at an airport.

        Attributes:
            number_of_agents
        """
    number_of_agents = 0
    def __init__(self, ctx):
        """
        Initializes a Coach class check-in counter object.
        :param ctx: SimulationContext (env, logger, simulation_time).
        """
        super().__init__(ctx)
        CoachCounter.number_of_agents += 1
        self.counter_type = "Coach"
        self.station_name = f"Coach Counter {CoachCounter.number_of_agents}"

    # todo if allocation policy allows for business passengers to use coach counter, then this method should be updated
    def handle_check_in(self, passenger):
        """
                Handle the check-in process for a coach passenger.

                Args:
                    passenger (Passenger): The passenger to check in.
                """
        with self.counter.request() as req:
            queue_entry_time = self.env.now
            self.logger.log_event(passenger.arrival_time, 'Check-in Queue', self.env.now,
                                  'Entered coach check-in queue',
                                  passenger_id=passenger.id, station=self.station_name)
            yield req
            wait_time = self.env.now - queue_entry_time
            self.logger.log_event(passenger.arrival_time, 'Check-in Start', self.env.now,
                                  'Started coach check-in service',
                                  passenger_id=passenger.id, station=self.station_name,
                                  duration=wait_time)
            boarding_pass_time = self.print_boarding_pass()
            bag_check_time = self.check_bags(passenger)
            problem_delay_time = self.handle_problems_and_delays()
            total_time = boarding_pass_time + bag_check_time + problem_delay_time
            print(f"Coach passenger {passenger.arrival_time} is at the counter.")
            yield self.env.timeout(total_time)  # Use SimPy's timeout for service time
            self.logger.log_event(passenger.arrival_time, 'Check-in', self.env.now, f'C. service time:{total_time}',
                                  passenger_id=passenger.id, station=self.station_name,
                                  duration=total_time)
