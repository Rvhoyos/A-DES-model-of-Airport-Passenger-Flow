import pandas as pd
import os


def parse_logs(log_directory):
    all_logs = pd.DataFrame()  # DataFrame to store all log data

    for filename in os.listdir(log_directory):
        if filename.endswith(".csv"):
            file_path = os.path.join(log_directory, filename)
            daily_log = pd.read_csv(file_path)
            all_logs = pd.concat([all_logs, daily_log], ignore_index=True)

    return all_logs


def main():
    log_directory = 'C:\\Users\\Thank\\PycharmProjects\\DES4005\\src\\airport\\data'
    parsed_data = parse_logs(log_directory)
    print(parsed_data.head())  # Print the first few rows to check the data


if __name__ == "__main__":
    main()
