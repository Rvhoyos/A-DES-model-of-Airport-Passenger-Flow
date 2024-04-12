import pandas as pd
from parser import parse_logs


def consolidate_passenger_logs(logs_df):
    # Initialize an empty list to hold the consolidated passenger data
    consolidated_data = []
    # Group the DataFrame by 'Arrival Time' to process each passenger's logs
    for _, group in logs_df.groupby('Arrival Time'):
        passenger_data = {
            'Arrival Time': group['Arrival Time'].iloc[0],
            'Events': list(group['Event']),
            'Times': list(group['Time']),
            'Details': list(group['Details']),
            # Extract additional fields as needed
        }
        # Append the passenger's data dictionary to the list
        consolidated_data.append(passenger_data)
    # Convert the list of dictionaries to a DataFrame for visualization and analysis
    return pd.DataFrame(consolidated_data)


def main():
    log_directory = 'C:\\Users\\Thank\\PycharmProjects\\DES4005\\src\\airport\\data'
    all_logs = parse_logs(log_directory)  # Get all logs parsed by the original function
    consolidated_logs = consolidate_passenger_logs(all_logs)

    # Export the consolidated logs to a CSV file
    output_file_path = ('C:\\Users\\Thank\\PycharmProjects\\DES4005\\src\\airport\\data\\analytics\\consolidated_logs'
                        '.csv')
    consolidated_logs.to_csv(output_file_path, index=False)
    print(f"Consolidated logs have been saved to {output_file_path}")


if __name__ == "__main__":
    main()
