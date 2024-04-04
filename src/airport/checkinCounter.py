import numpy as np
import simpy
from abc import ABC, abstractmethod


class CheckinCounter(ABC):
    """
      Abstract base class for a check-in counter at an airport.

      Attributes:
          env (simpy.Environment): The simulation environment.
          counter (simpy.Resource): SimPy resource representing the check-in counter.
          logger (Logger): Logger instance for event logging.
      """
    def __init__(self, env, logger):
        """
              Initialize a check-in counter.

              Args:
                  env (simpy.Environment): The simulation environment.
                  logger (Logger): Instance for logging events.
              """
        self.env = env
        self.counter = simpy.Resource(env, capacity=1)
        self.logger = logger

    @abstractmethod
    def handle_check_in(self, passenger):
        """
                Abstract method to handle the check-in process for a passenger.

                Args:
                    passenger (Passenger): The passenger to check in.
                """
        pass

    def print_boarding_pass(self):
        """Simulates the time taken to print a boarding pass."""
        return np.random.exponential(2 * 60)

    def check_bags(self, passenger):
        """
              Simulates the time taken to check bags.

              Args:
                  passenger (Passenger): The passenger checking in bags.
              """
        return passenger.num_bags * np.random.exponential(1 * 60) if passenger.num_bags > 0 else 0

    def handle_problems_and_delays(self):
        """Simulates the time taken to handle problems and delays."""
        return np.random.exponential(3 * 60)
