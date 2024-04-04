import numpy as np
import simpy
from src.airport.airport import Airport
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
        self.airport = Airport(self.env, simulation_time, num_business_counters, num_coach_counters, self.logger)  # Pass the Logger instance to the Airport class


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
            gate_type = 'commuter' if is_commuter else 'provincial'
            passenger = Passenger(gate_type, seat_type, arrival_time)
            self.env.process(self.airport.process_passenger(passenger))
            # Log passenger arrival
            self.logger.log_event(arrival_time, 'Arrival', self.env.now, f'Passenger arrived')

    def run(self):
        """
        Runs the simulation.
        """
        print(f"Simulation starting at time {self.env.now}")
        self.env.process(self.generate_passenger_arrivals())
        self.env.process(self.airport.regional_gate.process_queue())  # Process passengers in queue
        self.env.run(until=self.simulation_time)
        print(f"Simulation ended at time {self.env.now}")

# Main function to start the simulation
def main():
    simulation_days = int(input("Enter the number of days to run the simulation: "))
    num_business_counters = int(input("Enter the number of business class counters: "))
    num_coach_counters = int(input("Enter the number of coach counters: "))

    simulation_time = 86400 * simulation_days + 3600  # extra hour to ensure full day inclusion

    simulation = Simulation(simulation_time, num_business_counters, num_coach_counters)

    simulation.run()

if __name__ == "__main__":
    main()