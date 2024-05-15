class Flight:
    """
    Represents a flight in the airport simulation.
    Each flight has a type (regional or provincial), a departure time, and a number of available seats.
    Attributes:
        flight_type (str): The type of flight, either 'regional' or 'provincial'.
        departure_time (int): The time at which the flight is scheduled to depart.
        total_seats (dict): The total number of seats on the flight.
        available_seats (dict): The number of available seats on the flight.
        number (int): The unique flight number assigned to the flight.
        operation_cost (int): An ongoing sum of all the simulated costs of operating each flight.
    """
    flight_number = 0  # static variable to keep track of the number of flights
    flight_cost = 0

    def __init__(self, flight_type, departure_time):
        """
        Initializes a flight object with a flight type and departure time.
        :param flight_type:
        :param departure_time:
        """
        self.flight_type = flight_type
        self.departure_time = departure_time  # Set the departure time when creating the flight
        if flight_type == 'regional':
            self.total_seats = {'coach': 40}
            self.available_seats = {'coach': 40}
        elif flight_type == 'provincial':
            self.total_seats = {'coach': 140, 'business': 40}
            self.available_seats = {'coach': 140, 'business': 40}
        Flight.flight_number += 1  # Increment the flight number each time a new flight is created
        self.number = Flight.flight_number  # Assign flight number
        self.operation_cost = 12000 if type == 'provincial' else 1500
        Flight.flight_cost += self.operation_cost

    def board_passenger(self, passenger):
        """
        Boards a passenger onto the flight if there are available seats of the passenger's type.
        :param passenger:
        :return:
        """
        seat_type = passenger.seat_type
        if self.available_seats[seat_type] > 0: # Check if there are available seats of the passenger type
            self.available_seats[seat_type] -= 1
            return True
        return False

    def departure_log(self, logger):
        """
        Logs the departure of the flight.
        :param logger:
        :return:
        """
        print(f"Flight {self.number} is departing at time {self.departure_time}")  # New print statement
        details = f'Flight {self.number} departed with {self.available_seats} seats left out of {self.total_seats}'
        logger.log_event(self.departure_time, 'Flight Departure', self.departure_time, details)

    def __str__(self):
        """
        String representation of the flight object.
        :return:
        """
        return f"Flight({self.flight_type}, {self.available_seats})"
