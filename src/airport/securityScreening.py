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
    number_of_stations = 0

    def __init__(self, ctx):
        """
             Initializes the security screening process.

             Args:
                 ctx (SimulationContext): env, logger, simulation_time.
             """
        self.ctx = ctx
        self.env = ctx.env
        self.logger = ctx.logger
        SecurityScreening.number_of_stations += 1
        self.station_name = f"Security Station {SecurityScreening.number_of_stations}"
        # Separate resources for business and coach passengers
        self.provincial_machine = simpy.Resource(ctx.env, capacity=1)
        self.regional_machine = simpy.Resource(ctx.env, capacity=2)

    def screen_passenger(self, passenger):
        """
             Simulates the screening process for a passenger.

             Args:
                 passenger (Passenger): The passenger undergoing security screening.
             """
        # Choose the machine based on passenger gate type (region) (resource)
        machine = self.provincial_machine if passenger.gate_type == 'provincial' else self.regional_machine

        with machine.request() as req:
            queue_entry_time = self.env.now
            self.logger.log_event(passenger.arrival_time, 'Security Queue', self.env.now,
                                  'Entered security screening queue',
                                  passenger_id=passenger.id, station=self.station_name)
            yield req
            wait_time = self.env.now - queue_entry_time
            self.logger.log_event(passenger.arrival_time, 'Security Start', self.env.now,
                                  'Started security screening',
                                  passenger_id=passenger.id, station=self.station_name,
                                  duration=wait_time)
            screening_time = np.random.exponential(3 * 60)  # Screening time in seconds
            start_time = self.env.now
            yield self.env.timeout(screening_time)
            end_time = self.env.now
            print(f"Passenger {passenger.id} completed screening at {end_time}.")
            self.logger.log_event(
                passenger.arrival_time,
                'Security Screening',
                start_time,
                f'Screening completed in {screening_time} seconds',
                passenger_id=passenger.id, station=self.station_name, duration=screening_time
            )
