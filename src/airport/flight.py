class Flight:
    flight_number = 0  # static variable to keep track of the number of flights

    def __init__(self, flight_type, departure_time):
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

    def board_passenger(self, passenger):
        seat_type = passenger.seat_type
        if self.available_seats[seat_type] > 0:
            self.available_seats[seat_type] -= 1
            return True
        return False

    def __str__(self):
        return f"Flight({self.flight_type}, {self.available_seats})"
