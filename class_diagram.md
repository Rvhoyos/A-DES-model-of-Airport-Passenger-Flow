---
config:
  layout: elk
---
classDiagram
      class Simulation {
          -env : simpy.Environment
          -simulation_time : int
          -logger : Logger
          -ctx : SimulationContext
          -airport : Airport
          -interarrival_generator : ExponentialRNG
          +generate_passenger_arrivals()
          +print_and_log_totals()
          +run()
      }

      class SimulationContext {
          +env : simpy.Environment
          +logger : Logger
          +simulation_time : int
      }

      class Airport {
          -ctx : SimulationContext
          -env : simpy.Environment
          -logger : Logger
          -business_class_counters : list
          -coach_counters : list
          -security_screening : list
          -regional_gates : list
          -provincial_gates : list
          -_next_regional : int
          -_next_provincial : int
          +process_passenger(passenger)
          -_find_shortest_queue(stations, resources)
      }

      class Passenger {
          +gate_type : str
          +seat_type : str
          +arrival_time : float
          +num_bags : int
          +cost : int
          +id : int
          +passenger_count$ : int
          +ticket_revenue$ : int
          +generate_num_bags()
          +calculate_cost()
      }

      class Flight {
          +flight_type : str
          +departure_time : int
          +total_seats : dict
          +available_seats : dict
          +number : int
          +operation_cost : int
          +departed : bool
          +flight_number$ : int
          +flight_cost$ : int
          +board_passenger(passenger)
          +departure_log(logger)
      }

      class Logger {
          -env : simpy.Environment
          -log_dir : str
          -daily_log : list
          +COLUMNS$ : list
          +log_event(arrival_time, event, time, details, ...)
          +save_logs_periodically(interval)
          +save_daily_log(day)
          +reset_daily_log()
      }

      class CheckinCounter {
          <<abstract>>
          #ctx : SimulationContext
          #env : simpy.Environment
          #logger : Logger
          #counter : simpy.Resource
          +handle_check_in(passenger)*
          +print_boarding_pass()
          +check_bags(passenger)
          +handle_problems_and_delays()
      }

      class BusinessClassCounter {
          +number_of_agents$ : int
          +counter_type : str
          +station_name : str
          +handle_check_in(passenger)
      }

      class CoachCounter {
          +number_of_agents$ : int
          +counter_type : str
          +station_name : str
          +handle_check_in(passenger)
      }

      class SecurityScreening {
          -ctx : SimulationContext
          -env : simpy.Environment
          -logger : Logger
          -provincial_machine : simpy.Resource
          -regional_machine : simpy.Resource
          +number_of_stations$ : int
          +station_name : str
          +screen_passenger(passenger)
      }

      class Gate {
          <<abstract>>
          #ctx : SimulationContext
          #env : simpy.Environment
          #logger : Logger
          #current_flight : Flight
          +set_schedule()*
          +handle_passenger(passenger)*
          +find_current_flight(current_time)
          +schedule_departures()
      }

      class RegionalGate {
          +number_of_regional_gates$ : int
          +flight_schedule : list
          +queue : simpy.Store
          +gate_name : str
          +set_schedule(simulation_time)
          +handle_passenger(passenger)
          +process_queue()
      }

      class ProvincialGate {
          +number_of_provincial_gates$ : int
          +flight_schedule : list
          +gate_name : str
          +set_schedule(simulation_time)
          +handle_passenger(passenger)
      }

      class RandomNumberGenerator {
          <<abstract>>
          +generate()*
      }

      class ExponentialRandomNumberGenerator {
          -rate : float
          +generate()
      }

      class NormalRandomNumberGenerator {
          -mean : float
          -variance : float
          +generate()
      }

      class GeometricRandomNumberGenerator {
          -p : float
          +generate()
      }

      %% Inheritance
      CheckinCounter <|-- BusinessClassCounter
      CheckinCounter <|-- CoachCounter
      Gate <|-- RegionalGate
      Gate <|-- ProvincialGate
      RandomNumberGenerator <|-- ExponentialRandomNumberGenerator
      RandomNumberGenerator <|-- NormalRandomNumberGenerator
      RandomNumberGenerator <|-- GeometricRandomNumberGenerator

      %% Composition
      Simulation *-- Airport : owns
      Simulation *-- SimulationContext : owns
      Simulation *-- ExponentialRandomNumberGenerator : owns
      SimulationContext *-- Logger : owns
      Airport *-- CheckinCounter : "1..*"
      Airport *-- SecurityScreening : "1..*"
      Airport *-- Gate : "1..*"
      RegionalGate *-- Flight : "schedule"
      ProvincialGate *-- Flight : "schedule"

      %% Dependencies
      Airport ..> Passenger : processes
      SecurityScreening ..> Passenger : screens
      CheckinCounter ..> Passenger : checks in
      Gate ..> Passenger : boards
      Flight ..> Passenger : seats
