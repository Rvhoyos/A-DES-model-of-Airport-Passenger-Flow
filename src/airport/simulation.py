import numpy as np
import simpy
from src.airport.airport import Airport
from src.airport.businessCheckIn import BusinessClassCounter
from src.airport.coachCheckIn import CoachCounter
from src.airport.flight import Flight
from src.airport.logger import Logger
from src.airport.passenger import Passenger
from src.airport.checkinCounter import CheckinCounter
from src.airport.securityScreening import SecurityScreening
from src.airport.gate import Gate


# Simulation setup
class Simulation:
    def __init__(self, simulation_time, num_business_counters, num_coach_counters):
        """
            Initializes the simulation.

            :param simulation_time: Total time to run the simulation in seconds.
            :param airport: The airport object which will be used in the simulation.
            """
        self.env = simpy.Environment()
        self.simulation_time = simulation_time
        self.logger = Logger()
        self.airport = Airport(self.env, simulation_time, num_business_counters, num_coach_counters,
                               self.logger)  # Pass the Logger instance to the Airport class

    def generate_passenger_arrivals(self):
        """
        Generates passenger arrivals at the airport based on specified rates and distributions.
        """
        print("Starting passenger arrival generation")
        commuter_arrival_rate = 40 / 3600  # passengers per second
        provincial_mean_arrival_time = 75 * 60  # mean arrival time in seconds
        provincial_arrival_variance = 50 * 60 * 60  # variance in arrival time

        while True:
            is_commuter = np.random.rand() < 0.5
            if is_commuter:
                next_arrival_time = np.random.exponential(1 / commuter_arrival_rate)
                seat_type = 'coach'  # Assuming commuter flights only have coach seats
            else:
                next_arrival_time = np.random.normal(provincial_mean_arrival_time, np.sqrt(provincial_arrival_variance))
                seat_type = 'business' if np.random.rand() < 0.5 else 'coach'

            next_arrival_time = max(next_arrival_time, 0)  # Ensure non-negative time
            yield self.env.timeout(next_arrival_time)
            arrival_time = self.env.now
            self.logger.log_event(arrival_time, 'Arrival', arrival_time,
                                  'Passenger arrived')  # Log right after determining arrival_time
            gate_type = 'commuter' if is_commuter else 'provincial'
            passenger = Passenger(gate_type, seat_type, arrival_time)
            self.env.process(self.airport.process_passenger(passenger))  # Start processing the passenger

    def print_and_log_totals(self):
        total_revenue = Passenger.ticket_revenue
        total_flight_cost = Flight.flight_cost
        total_checkin_cost = (self.simulation_time / 3600)*(CoachCounter.number_of_agents)*(BusinessClassCounter.number_of_agents)
        total_cost = total_flight_cost + total_checkin_cost
        print(f"Toal Number of Passengers: {Passenger.passenger_count}")
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
        self.env.process(self.airport.regional_gate.process_queue())  # Process passengers in queue
        self.env.run(until=self.simulation_time)
        print(f"Simulation ended at time {self.env.now}")

def replicate(runs, simulation):
    for i in range(runs):
        simulation.run()
        simulation.print_and_log_totals()

# Main function to start the simulation
def main():
    simulation_days = int(input("Enter the number of days to run the simulation: "))
    num_business_counters = int(input("Enter the number of business class counters: "))
    num_coach_counters = int(input("Enter the number of coach counters: "))

    simulation_time = 86400 * simulation_days + 3600  # extra hour to ensure full day inclusion


    simulation = Simulation(simulation_time, num_business_counters, num_coach_counters)
    default_runs = 1 #todo add working replication runs for fun
    replicate(default_runs, simulation)

    #simulation.run()
    #simulation.print_and_log_totals()

if __name__ == "__main__":
    main()
