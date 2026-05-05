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
    Manages the airport's stations and routes passengers through them.

    Stations: check-in counters, security screening, gates.
    Each station wraps one or more simpy.Resource objects. A Resource
    models a real-world server with limited capacity (e.g. one agent
    at a counter). When a passenger requests a Resource that is busy,
    SimPy automatically queues them until it frees up.
    """

    def __init__(self, ctx, num_business_counters, num_coach_counters,
                 num_security_screens, num_regional_gates, num_provincial_gates):
        self.ctx = ctx
        self.env = ctx.env
        self.logger = ctx.logger

        self.business_class_counters = [BusinessClassCounter(ctx) for _ in range(num_business_counters)]
        self.coach_counters = [CoachCounter(ctx) for _ in range(num_coach_counters)]
        self.security_screening = [SecurityScreening(ctx) for _ in range(num_security_screens)]
        self.regional_gates = [RegionalGate(ctx) for _ in range(num_regional_gates)]
        self.provincial_gates = [ProvincialGate(ctx) for _ in range(num_provincial_gates)]

        # Round-robin counters for gate assignment.
        # Simple alternation (Gate 1, Gate 2, Gate 1, ...).
        self._next_regional = 0
        self._next_provincial = 0

    # --- Helpers ---

    def _find_shortest_queue(self, stations, resources):
        """
        Return the station with the fewest passengers waiting.

        Args:
            stations:  list of station objects (e.g. check-in counters or screening stations).
            resources: list of simpy.Resource objects, one per station, same order.
                       A Resource's .queue holds the passengers waiting for service.

        Loops through each station, checks how many passengers are in that
        station's resource queue, and returns whichever station has the fewest.
        """
        best_station = stations[0]
        best_length = len(resources[0].queue)

        for i in range(1, len(stations)):
            queue_length = len(resources[i].queue)
            if queue_length < best_length:
                best_length = queue_length
                best_station = stations[i]

        return best_station

    # --- Passenger pipeline ---

    def process_passenger(self, passenger):
        """
        Routes a passenger through check-in, security, and gate.

        This is a SimPy generator process. Each `yield self.env.process(X)`
        pauses this passenger's flow until sub-process X finishes, then
        resumes at the next line. This is how SimPy models sequential steps:
        the passenger "waits" at each station without blocking other passengers.
        """
        print(f"Processing passenger {passenger.id}")
        self.logger.log_event(passenger.arrival_time, 'Process Start', self.env.now,
                              f"Starting process for passenger",
                              passenger_id=passenger.id)

        # --- STAGE 1: CHECK-IN ---
        # Pick the counter with the shortest queue.
        # Each CheckinCounter has a .counter attribute which is a simpy.Resource(capacity=1).
        # BUG (TODO #1): handle_check_in() is never yielded here, so passengers skip check-in.
        if passenger.seat_type == 'business':
            counters = self.business_class_counters
        else:
            counters = self.coach_counters
        # .counter is the simpy.Resource on each CheckinCounter
        counter_resources = [c.counter for c in counters]
        counter = self._find_shortest_queue(counters, counter_resources)
        yield self.env.process(counter.handle_check_in(passenger))
        print(f"Passenger {passenger.id} has checked in")

        # --- STAGE 2: SECURITY SCREENING ---
        # Each SecurityScreening station has two simpy.Resources:
        #   .business_machine (capacity=1) and .coach_machines (capacity=2).
        # Pick the station where the relevant machine has the shortest queue.
        if passenger.gate_type == 'commuter':
            machines = [s.regional_machine for s in self.security_screening]
        else:
            machines = [s.provincial_machine for s in self.security_screening]
        chosen_screening = self._find_shortest_queue(self.security_screening, machines)
        yield self.env.process(chosen_screening.screen_passenger(passenger))
        print(f"Passenger {passenger.id} has cleared security screening")

        # --- STAGE 3: GATE ---
        # Route passenger to one gate via round-robin alternation.
        if passenger.gate_type == 'commuter':
            gate = self.regional_gates[self._next_regional % len(self.regional_gates)]
            self._next_regional += 1
        else:
            gate = self.provincial_gates[self._next_provincial % len(self.provincial_gates)]
            self._next_provincial += 1
        yield self.env.process(gate.handle_passenger(passenger))

