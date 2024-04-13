import os

import pandas as pd
from analyze_data import parse_logs


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


def analyze_event_types(logs_df):
    # Initialize an empty DataFrame to store detailed logs for each event type
    detailed_event_logs = pd.DataFrame()

    # Group by event type to process logs for each type
    for event_type, group in logs_df.groupby('Event'):
        # Extract and store relevant details for each event
        event_details = group[['Time', 'Details']].copy()
        event_details['Event Type'] = event_type  # Add the event type to the DataFrame #todo error in consol

        # Append to the detailed_event_logs DataFrame
        detailed_event_logs = pd.concat([detailed_event_logs, event_details], ignore_index=True)

    # Sort by event type and time for better readability
    detailed_event_logs.sort_values(by=['Event Type', 'Time'], inplace=True)

    return detailed_event_logs


# main method to run after the simulation.
# Parses logs, and sorts data into data frames for analysis
# First file exported consolidates passenger logs
# Second file exported analyzes event types
def main():
    log_directory = os.path.join(os.path.dirname(__file__), '..', 'data')
    all_logs = parse_logs(log_directory)  # Get all logs parsed by the original function
    consolidated_logs = consolidate_passenger_logs(all_logs)

    # Consolidate passenger logs and save to CSV
    output_file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'analytics', 'sorted_by_passenger_logs.csv')

    consolidated_logs.to_csv(output_file_path, index=False)
    print(f"Consolidated logs have been saved to {output_file_path}")

    # Analyze event types and save to CSV
    event_analysis = analyze_event_types(all_logs)
    event_analysis_output_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'analytics',
                                              'sorted_by_event_type_logs.csv')
    event_analysis.to_csv(event_analysis_output_path, index=False)
    print("Event analysis has been saved.")

if __name__ == "__main__":
    main()
