import os
import pandas as pd


class Logger:
    """
    Class to log events in the airport simulation.
    """
    def __init__(self, log_dir=None):
        """
        Initializes the logger with a directory to save logs.
        :param log_dir:
        """
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(__file__), 'data')
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.daily_log = pd.DataFrame(columns=['Arrival Time', 'Event', 'Time', 'Details',
                                                'Passenger ID', 'Gate Type', 'Seat Type', 'Station', 'Duration', 'Bags', 'Cost'])

    def log_event(self, arrival_time, event, time, details,
                  passenger_id=None, gate_type=None, seat_type=None, station=None, duration=None, num_bags=None, cost=None):
        """
        Logs an event with arrival time, event type, time, and details.
        :param arrival_time:
        :param event:
        :param time:
        :param details:
        :param passenger_id:
        :param gate_type:
        :param seat_type:
        :param station:
        :param duration:
        :return:
        """
        print(f"Logging event: {event}, Time: {time}, Details: {details}")
        new_record = pd.DataFrame({
            'Arrival Time': [arrival_time], 'Event': [event], 'Time': [time], 'Details': [details],
            'Passenger ID': [passenger_id], 'Gate Type': [gate_type], 'Seat Type': [seat_type],
            'Station': [station], 'Duration': [duration], 'Bags': [num_bags], 'Cost': [cost]
        })
        self.daily_log = pd.concat([self.daily_log, new_record], ignore_index=True)

    def reset_daily_log(self):
        """
        Resets the daily log to an empty DataFrame.
        :return:
        """
        self.daily_log = pd.DataFrame(columns=['Arrival Time', 'Event', 'Time', 'Details',
                                                'Passenger ID', 'Gate Type', 'Seat Type', 'Station', 'Duration', 'Bags', 'Cost'])

    def save_daily_log(self, day):
        """
        Saves the daily log to a CSV file.
        :param day:
        :return:
        """
        filepath = os.path.join(self.log_dir, f'day_{day}_log.csv')
        self.daily_log.to_csv(filepath, index=False)
