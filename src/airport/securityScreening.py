import numpy as np
import simpy


class SecurityScreening:
    """
    Represents the security screening process at an airport.

    Attributes:
        env (simpy.Environment): The simulation environment.
        business_machine (simpy.Resource): SimPy resource representing the screening machine for business class passengers.
        coach_machines (simpy.Resource): SimPy resource representing the screening machines for coach passengers.
        logger (Logger): Logger instance for event logging.
    """
    def __init__(self, ctx):
        """
             Initializes the security screening process.

             Args:
                 ctx (SimulationContext): Shared simulation dependencies.
             """
        self.ctx = ctx
        self.env = ctx.env
        self.logger = ctx.logger
        # Separate resources for business and coach passengers
        self.business_machine = simpy.Resource(ctx.env, capacity=1)
        self.coach_machines = simpy.Resource(ctx.env, capacity=2)

    def screen_passenger(self, passenger):
        """
             Simulates the screening process for a passenger.

             Args:
                 passenger (Passenger): The passenger undergoing security screening.
             """
        # Choose the machine based on passenger seat type
        machine = self.business_machine if passenger.seat_type == 'business' else self.coach_machines

        with machine.request() as req:
            yield req
            screening_time = np.random.exponential(3 * 60)  # Screening time in seconds
            start_time = self.env.now
            yield self.env.timeout(screening_time)
            end_time = self.env.now
            print(f"Passenger {passenger.arrival_time} completed screening at {end_time}.")
            self.logger.log_event(
                passenger.arrival_time,
                'Security Screening',
                start_time,
                f'Screening completed in {screening_time} seconds'
            )
