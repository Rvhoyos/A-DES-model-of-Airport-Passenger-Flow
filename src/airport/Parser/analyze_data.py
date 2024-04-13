import pandas as pd
import os


# Parses log files from a directory and returns a DataFrame
def parse_logs(log_directory):
    all_logs = pd.DataFrame()  # DataFrame to store all log data

    for filename in os.listdir(log_directory):
        if filename.endswith(".csv"):
            file_path = os.path.join(log_directory, filename)
            daily_log = pd.read_csv(file_path)
            all_logs = pd.concat([all_logs, daily_log], ignore_index=True)
    return all_logs


def analyze_passenger_service_times(filepath):
    df = pd.read_csv(filepath)
    # Ensure 'Times' column is a list of numeric values
    df['Times'] = df['Times'].apply(lambda x: [float(t) for t in eval(x)])
    # Calculate service time for each passenger
    service_times = df['Times'].apply(lambda times: max(times) - min(times))
    return service_times.describe()


def analyze_event_service_times(filepath):
    df = pd.read_csv(filepath)
    # Convert 'Time' to float for numerical operations
    df['Time'] = df['Time'].astype(float)
    # Group by 'Event Type' and calculate statistics for each type
    stats = df.groupby('Event Type')['Time'].agg(['mean', 'std', 'min', 'max'])
    return stats


def main():
    log_directory = os.path.join(os.path.dirname(__file__), '..', 'data')
    parsed_data = parse_logs(log_directory)
    print(parsed_data.head(3))
    print(parsed_data.tail(3))
    analytics_directory = os.path.join(os.path.dirname(__file__), '..', 'data', 'analytics')
    passenger_service_stats = analyze_passenger_service_times(
        os.path.join(analytics_directory, 'sorted_by_passenger_logs.csv'))
    event_service_stats = analyze_event_service_times(
        os.path.join(analytics_directory, 'sorted_by_event_type_logs.csv'))

    print("Passenger Service Times Statistics:")
    print(passenger_service_stats)
    passenger_service_stats.to_csv(os.path.join(analytics_directory, 'passenger_service_times_stats.csv'))

    print("\nEvent Type Service Times Statistics:")
    print(event_service_stats)
    passenger_service_stats.to_csv(os.path.join(analytics_directory, 'event_service_times_stats.csv'))


if __name__ == "__main__":
    main()
# todo remove main method and call parser from log_functions.py
