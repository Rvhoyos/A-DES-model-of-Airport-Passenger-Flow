import os
import pandas as pd


class Logger:
    """
    Class to log events in the airport simulation.
    """

    COLUMNS = [
        'Arrival Time', 'Event', 'Time', 'Details',
        'Passenger ID', 'Gate Type', 'Seat Type', 'Station', 
        'Duration', 'Bags', 'Cost'
    ]
    
    def __init__(self, env, log_dir=None):
        """
        Initializes the logger with a directory to save logs.
        :param env: SimPy environment (used for periodic log saving).
        :param log_dir:
        """
        self.env = env
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(__file__), 'data')
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.daily_log = []
        self.env.process(self.save_logs_periodically(86400))

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
        self.daily_log.append({
            'Arrival Time': arrival_time, 'Event': event, 'Time': time, 'Details': details,
            'Passenger ID': passenger_id, 'Gate Type': gate_type, 'Seat Type': seat_type,
            'Station': station, 'Duration': duration, 'Bags': num_bags, 'Cost': cost
        })

    def reset_daily_log(self):
        """
        Resets the daily log to an empty list.
        :return:
        """
        self.daily_log = []

    def save_logs_periodically(self, interval):
        """
        A process that saves logs at regular intervals (e.g., daily).
        """
        while True:
            yield self.env.timeout(interval)
            day = int(self.env.now / interval)
            self.save_daily_log(day)
            self.reset_daily_log()

    def save_daily_log(self, day):
        """
        Saves the daily log to a CSV file.
        :param day:
        :return:
        """
        filepath = os.path.join(self.log_dir, f'day_{day}_log.csv')
        pd.DataFrame(self.daily_log, columns=self.COLUMNS).to_csv(filepath, index=False)
