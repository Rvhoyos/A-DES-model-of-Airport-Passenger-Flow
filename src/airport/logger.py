import os
import pandas as pd


class Logger:
    """
    Class to log events in the airport simulation.
    """
    def __init__(self, log_dir='data'):
        """
        Initializes the logger with a directory to save logs.
        :param log_dir:
        """
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.daily_log = pd.DataFrame(columns=['Arrival Time', 'Event', 'Time', 'Details'])

    def log_event(self, arrival_time, event, time, details):
        """
        Logs an event with arrival time, event type, time, and details.
        :param arrival_time:
        :param event:
        :param time:
        :param details:
        :return:
        """
        print(f"Logging event: {event}, Time: {time}, Details: {details}")
        new_record = pd.DataFrame(
            {'Arrival Time': [arrival_time], 'Event': [event], 'Time': [time], 'Details': [details]})
        self.daily_log = pd.concat([self.daily_log, new_record], ignore_index=True)

    def reset_daily_log(self):
        """
        Resets the daily log to an empty DataFrame.
        :return:
        """
        self.daily_log = pd.DataFrame(columns=['Arrival Time', 'Event', 'Time', 'Details'])

    def save_daily_log(self, day):
        """
        Saves the daily log to a CSV file.
        :param day:
        :return:
        """
        filepath = os.path.join(self.log_dir, f'day_{day}_log.csv')
        self.daily_log.to_csv(filepath, index=False)
