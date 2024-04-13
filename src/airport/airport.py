import simpy

from .logger import Logger
from .flight import Flight
from .securityScreening import SecurityScreening
from .provincialGate import ProvincialGate
from .regionalGate import RegionalGate
from .businessCheckIn import BusinessClassCounter
from .coachCheckIn import CoachCounter


class Airport:
    """
        Represents an airport in a simulation, managing its various counters,
        security screening, and gates.

        Attributes:
            env (simpy.Environment): The simulation environment.
            logger (Logger): The logger instance for logging events in the airport.
            business_class_counters (list): List of counters for business class check-ins.
            coach_counters (list): List of counters for coach check-ins.
            security_screening (SecurityScreening): The security screening component.
            regional_gate (RegionalGate): The gate for regional flights.
            provincial_gate (ProvincialGate): The gate for provincial flights.
        """

    def __init__(self, env, simulation_time, num_business_counters, num_coach_counters, logger):
        """
                Initializes the airport simulation.

                Args:
                    env (simpy.Environment): The simulation environment.
                    simulation_time (int): Total simulation time in seconds.
                    num_business_counters (int): Number of business class counters.
                    num_coach_counters (int): Number of coach counters.
                """
        self.env = env
        self.logger = logger

        # Pass the logger to each component of the airport
        self.business_class_counters = [BusinessClassCounter(env, self.logger) for _ in
                                        range(num_business_counters)]  # 1 counter for business class
        self.coach_counters = [CoachCounter(env, logger) for _ in range(num_coach_counters)]  # 3 counters for coach

        self.security_screening = SecurityScreening(env, logger)

        self.regional_gate = RegionalGate(env, logger, simulation_time)  # Pass simulation_time to RegionalGate
        self.provincial_gate = ProvincialGate(env, logger, simulation_time)  # Pass simulation_time to ProvincialGate
        self.start_log_saving_process(86400)  # 86400 seconds in a day / log interval

    # todo call object.logger.save in this method?
    def process_passenger(self, passenger):
        """
        Processes a passenger through the airport's check-in, security, and gate.
        Args:
            passenger (Passenger): The passenger to process.
            """
        print(f"Processing passenger {passenger.arrival_time}")
        self.logger.log_event(passenger.arrival_time, 'Process Start', self.env.now,
                              f"Starting process for passenger")
        # Determine which counter to use based on passenger type
        if passenger.seat_type == 'business':
            counter = self.business_class_counters[
                0]  # Assuming a single business class counter todo implement allocation policy for dynamic counter amount.
        else:
            counter = self.coach_counters[0]
        # Proceed with subprocess for passenger check-in
        yield self.env.process(counter.handle_check_in(passenger))
        print(f"Passenger {passenger.arrival_time} has checked in")
        # todo above print statement is not executed, verify handle checking
        # Proceed to security screening
        yield self.env.process(self.security_screening.screen_passenger(passenger))

        # Finally, handle the passenger at the appropriate gate
        if passenger.gate_type == 'commuter':
            yield self.env.process(self.regional_gate.handle_passenger(passenger))
        else:
            yield self.env.process(self.provincial_gate.handle_passenger(passenger))

    def save_logs(self, day):
        """
        Saves the daily logs for the specified day.
        """
        self.logger.save_daily_log(day)
        self.logger.reset_daily_log()

    def start_log_saving_process(self, interval):
        """
        Starts the log-saving process to save logs periodically.
        """
        self.env.process(self.save_logs_periodically(interval))

    def save_logs_periodically(self, interval):
        """
        A process that saves logs at regular intervals (e.g., daily).
        """
        while True:
            yield self.env.timeout(interval)
            day = int(self.env.now / interval)
            self.save_logs(day)
