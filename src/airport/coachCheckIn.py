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
        :param ctx: SimulationContext with shared dependencies.
        """
        super().__init__(ctx)
        self.counter_type = "Coach"
        CoachCounter.number_of_agents += 1

    # todo if allocation policy allows for business passengers to use coach counter, then this method should be updated
    def handle_check_in(self, passenger):
        """
                Handle the check-in process for a coach passenger.

                Args:
                    passenger (Passenger): The passenger to check in.
                """
        with self.counter.request() as req:
            yield req
            boarding_pass_time = self.print_boarding_pass()
            bag_check_time = self.check_bags(passenger)
            problem_delay_time = self.handle_problems_and_delays()
            total_time = boarding_pass_time + bag_check_time + problem_delay_time
            print(f"Coach passenger {passenger.arrival_time} is at the counter.")
            yield self.env.timeout(total_time)  # Use SimPy's timeout for service time
            self.logger.log_event(passenger.arrival_time, 'Check-in', self.env.now, f'C. service time:{total_time}')
