import numpy as np
import simpy

from src.airport.RVG.randomNumberGenerator import ExponentialRandomNumberGenerator
from src.airport.airport import Airport
from src.airport.businessCheckIn import BusinessClassCounter
from src.airport.coachCheckIn import CoachCounter
from src.airport.context import SimulationContext
from src.airport.flight import Flight
from src.airport.logger import Logger
from src.airport.passenger import Passenger
from src.airport.checkinCounter import CheckinCounter
from src.airport.securityScreening import SecurityScreening
from src.airport.gate import Gate


class Simulation:
    """
    Represents a simulation of an airport handling passengers through a series of workstations.
    The workstations serve the passengers based on the queuing model of each workstation.
    Service times are generated using Simpy's "Yield" to clock delays in the simulation environment.
    Numpy's random number distributions are used to generate random service times for each workstation.
    Wait times depend on queuing models, average service time of passengers and line capacity of each workstation.
    """
    def __init__(self, simulation_time, num_business_counters, num_coach_counters, interarrival_rate, num_security_screens, num_regional_gates, num_provincial_gates):
        """
        Initializes the simulation with a specified simulation time and number of counters.
        :param simulation_time, num_business_counters, num_coach_counters:
        """
        self.env = simpy.Environment()
        self.simulation_time = simulation_time
        self.logger = Logger()
        self.ctx = SimulationContext(env=self.env, logger=self.logger, simulation_time=simulation_time)
        self.airport = Airport(self.ctx, num_business_counters, num_coach_counters, num_security_screens, num_regional_gates, num_provincial_gates)
        self.interarrival_generator = ExponentialRandomNumberGenerator(interarrival_rate / 3600)  # Poisson process: inter-arrival times are exponentially distributed. Convert passengers/hour to passengers/second.

    def generate_passenger_arrivals(self):
        """
        Generates passenger arrivals at the airport using one Poisson process.
        All passengers share the same exponential inter-arrival generator (user's input rate).
        After arrival, each passenger is classified as commuter or provincial.
        """
        print("Starting passenger arrival generation")

        while True:
            next_arrival_time = self.interarrival_generator.generate()
            yield self.env.timeout(next_arrival_time)
            arrival_time = self.env.now

            is_commuter = np.random.rand() < 0.5
            gate_type = 'commuter' if is_commuter else 'provincial'

            if is_commuter:
                seat_type = 'coach'
            else:
                seat_type = 'business' if np.random.rand() < 0.5 else 'coach'

            self.logger.log_event(arrival_time, 'Arrival', arrival_time, 'Passenger arrived')
            passenger = Passenger(gate_type, seat_type, arrival_time)
            self.env.process(self.airport.process_passenger(passenger))

    def print_and_log_totals(self):
        """
        At simulation end time.
        Prints and logs the important metrics of the simulation.
        :return:
        """
        total_revenue = Passenger.ticket_revenue
        total_flight_cost = Flight.flight_cost
        total_checkin_cost = (self.simulation_time / 3600) * (CoachCounter.number_of_agents) * (
            BusinessClassCounter.number_of_agents)
        total_cost = total_flight_cost + total_checkin_cost
        print(f"Total Number of Passengers: {Passenger.passenger_count}")
        print(f"Total number of flights: {Flight.flight_number}")
        print(f"Total Agents: {CoachCounter.number_of_agents + BusinessClassCounter.number_of_agents}")
        print(f"Total revenue: ${total_revenue}")
        print(f"Flights cost: ${total_flight_cost}")
        print(f"Counters cost: ${total_checkin_cost}")
        print(f"Total cost: ${total_cost}")
        self.logger.log_event(self.env.now, 'Total Revenue', self.env.now, f"Total revenue: ${total_revenue}")
        self.logger.log_event(self.env.now, 'Total Cost', self.env.now, f"Total cost: ${total_cost}")

    def run(self):
        """
        Runs the simulation.
        """
        print(f"Simulation starting at time {self.env.now}")
        self.env.process(self.generate_passenger_arrivals())
        for gate in self.airport.regional_gates:
            self.env.process(gate.process_queue())  # Process passengers in queue
        self.env.run(until=self.simulation_time)
        print(f"Simulation ended at time {self.env.now}")


def replicate(runs, simulation):
    """
    Replicates the simulation for a specified number of runs.
    :param runs:
    :param simulation:
    todo add working replication runs
    """
    for i in range(runs):
        simulation.run()
        simulation.print_and_log_totals()


# Main function to start the simulation
def main():
    simulation_days = int(input("Enter the number of days to run the simulation: "))
    num_business_counters = int(input("Enter the number of business class counters: "))
    num_coach_counters = int(input("Enter the number of coach counters: "))
    num_security_screens = int(input("Enter the number of security screening stations: "))
    num_regional_gates = int(input("Enter the number of regional gates: "))
    num_provincial_gates = int(input("Enter the number of provincial gates: "))
    interarrival_rate = float(input("Enter the passenger arrival rate (passengers per hour): "))

    simulation_time = 86400 * simulation_days + 3600  # extra hour to ensure full day inclusion

    simulation = Simulation(simulation_time, num_business_counters, num_coach_counters, interarrival_rate, num_security_screens, num_regional_gates, num_provincial_gates)
    default_runs = 1 #change when replication is working
    replicate(default_runs, simulation)


if __name__ == "__main__":
    main()
