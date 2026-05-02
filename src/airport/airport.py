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

    def __init__(self, ctx, num_business_counters, num_coach_counters, num_security_screens, num_regional_gates, num_provincial_gates):
        """
                Initializes the airport simulation.

                Args:
                    ctx (SimulationContext): env, logger, simulation_time.
                    num_business_counters (int): Number of business class counters.
                    num_coach_counters (int): Number of coach counters.
                    num_security_screens (int): Number of security screening stations.
                    num_regional_gates (int): Number of regional gates.
                    num_provincial_gates (int): Number of provincial gates.
                """
        self.ctx = ctx
        self.env = ctx.env
        self.logger = ctx.logger

        self.business_class_counters = [BusinessClassCounter(ctx) for _ in range(num_business_counters)]
        self.coach_counters = [CoachCounter(ctx) for _ in range(num_coach_counters)]
        self.security_screening = [SecurityScreening(ctx) for _ in range(num_security_screens)]
        self.regional_gates = [RegionalGate(ctx) for _ in range(num_regional_gates)]
        self.provincial_gates = [ProvincialGate(ctx) for _ in range(num_provincial_gates)]
        self.start_log_saving_process(86400)  # 86400 seconds in a day / log interval

    def process_passenger(self, passenger):
        """
        SimPy generator process: routes a passenger through check-in → security → gate.

        Each `yield self.env.process(...)` suspends this generator until the sub-process
        completes. SimPy resumes execution at the next line once the yielded event fires.
        See: docs/simpy_4.1.1_api_reference.md -"Sequential sub-processes"

        Args:
            passenger (Passenger): The passenger to process.
        """
        print(f"Processing passenger {passenger.arrival_time}")
        self.logger.log_event(passenger.arrival_time, 'Process Start', self.env.now,
                              f"Starting process for passenger",
                              passenger_id=passenger.id, gate_type=passenger.gate_type,
                              seat_type=passenger.seat_type)

        # --- STAGE 1: CHECK-IN ---
        # counter is a simpy.Resource (capacity=1). Its handle_check_in() is a
        # generator that does: yield req → yield env.timeout(service_time).
        # To actually run it, SimPy needs: yield self.env.process(counter.handle_check_in(passenger))
        # Without that yield, the counter is selected but never used -passenger skips to security.
        if passenger.seat_type == 'business':
            counter = min(self.business_class_counters, key=lambda c: len(c.counter.queue))
        else:
            counter = min(self.coach_counters, key=lambda c: len(c.counter.queue))

        # --- STAGE 2: SECURITY SCREENING ---
        # Picks the screening station with the shortest queue.
        # Shortest-queue selection: .queue on simpy.Resource holds waiting requests.
        # See: docs/simpy_4.1.1_api_reference.md -BaseResource hierarchy
        min_queue_length = float('inf')
        chosen_screening = None
        for screening in self.security_screening:
            if passenger.seat_type == 'business':
                queue_length = len(screening.business_machine.queue)
            else:
                queue_length = len(screening.coach_machines.queue)
            if queue_length < min_queue_length:
                min_queue_length = queue_length
                chosen_screening = screening
        yield self.env.process(chosen_screening.screen_passenger(passenger))
        print(f"Passenger {passenger.arrival_time} has checked in")

        # --- STAGE 3: GATE ---
        # BUG: the for loop yields a process for EVERY gate of this type.
        # yield self.env.process() is blocking -it waits for each gate's handle_passenger()
        # to finish, then moves to the next gate. So one passenger sequentially visits
        # every gate and potentially boards multiple flights.
        # A passenger should go to ONE gate (e.g., the one with the next available flight).
        if passenger.gate_type == 'commuter':
            for gate in self.regional_gates:
                yield self.env.process(gate.handle_passenger(passenger))
        else:
            for gate in self.provincial_gates:
                yield self.env.process(gate.handle_passenger(passenger))

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
