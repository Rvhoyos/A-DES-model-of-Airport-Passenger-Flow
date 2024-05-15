from .checkinCounter import CheckinCounter
from .logger import Logger


class BusinessClassCounter(CheckinCounter):
    """
        Represents a business class check-in counter at an airport.

        Attributes:
            number_of_agents
            env (simpy.Environment): The simulation environment.
            logger (Logger): Logger instance for event logging.
    """
    number_of_agents = 0  # Static variable to keep track of the number of business class counters

    def __init__(self, env, logger):
        """
        Initializes a business class check-in counter object with a simulation environment and a logger.
        :param env:
        :param logger:
        """
        super().__init__(env, logger)  # Pass the environment to the superclass
        self.counter_type = "Business Class"
        BusinessClassCounter.number_of_agents += 1

    def handle_check_in(self, passenger):
        """
              Handle the check-in process for a business class passenger.

              Args:
                  passenger (Passenger): The passenger to check in.
              """
        with self.counter.request() as req:
            yield req
            boarding_pass_time = self.print_boarding_pass()
            bag_check_time = self.check_bags(passenger)
            problem_delay_time = self.handle_problems_and_delays()
            total_time = boarding_pass_time + bag_check_time + problem_delay_time
            print(f"Business passenger {passenger.arrival_time} is at the counter.")
            yield self.env.timeout(total_time)  # Use SimPy's timeout for service time
            self.logger.log_event(passenger.arrival_time, 'Check-in', self.env.now, f'B. service time:{total_time}')
