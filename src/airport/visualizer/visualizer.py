import pandas as pd
import matplotlib.pyplot as plt
import os


def visualize_logs(
        log_dir='C:\\Users\\Thank\\PycharmProjects\\DES4005\\src\\airport\\data'):  # Replace with the absolute path to your 'data' directory
    for filename in os.listdir(log_dir):
        if filename.endswith('.csv'):
            filepath = os.path.join(log_dir, filename)
            df = pd.read_csv(filepath)
            plt.figure(figsize=(10, 6))
            df['Time'].hist(bins=50)
            plt.title(f'Event Distribution on {filename.strip(".csv")}')
            plt.xlabel('Time (seconds)')
            plt.ylabel('Number of Events')
            plt.show()

    # visualize logs for all check in counters


# visualize logs for all check in counters
def visualize_logs_counters(log_dir='C:\\Users\\Thank\\PycharmProjects\\DES4005\\src\\airport\\data'):
    for filename in os.listdir(log_dir):
        if filename.endswith('.csv'):
            filepath = os.path.join(log_dir, filename)
            df = pd.read_csv(filepath)
            df_counters = df[df['Details'].str.contains('service time')]
            plt.figure(figsize=(10, 6))
            df_counters['Time'].hist(bins=50)
            plt.title(f'Check-in Counters Event Distribution on {filename.strip(".csv")}')
            plt.xlabel('Time (seconds)')
            plt.ylabel('Number of Events')
            plt.show()


# visualize RAW logs found in the data folder
# todo add Visualizations for anaalytics folder.
def visualize_logs_screening(log_dir='C:\\Users\\Thank\\PycharmProjects\\DES4005\\src\\airport\\data'):
    for filename in os.listdir(log_dir):
        if filename.endswith('.csv'):
            filepath = os.path.join(log_dir, filename)
            df = pd.read_csv(filepath)
            df_screening = df[df['Event'] == 'Security Screening']
            plt.figure(figsize=(10, 6))
            df_screening['Time'].hist(bins=50)
            plt.title(f'Security Screening Event Distribution on {filename.strip(".csv")}')
            plt.xlabel('Time (seconds)')
            plt.ylabel('Number of Events')
            plt.show()


# Visualize logs for all gates
def visualize_logs_gates(log_dir='C:\\Users\\Thank\\PycharmProjects\\DES4005\\src\\airport\\data'):
    for filename in os.listdir(log_dir):
        if filename.endswith('.csv'):
            filepath = os.path.join(log_dir, filename)
            df = pd.read_csv(filepath)
            df_gates = df[df['Event'] == 'Boarding']
            plt.figure(figsize=(10, 6))
            df_gates['Time'].hist(bins=50)
            plt.title(f'Gates Event Distribution on {filename.strip(".csv")}')
            plt.xlabel('Time (seconds)')
            plt.ylabel('Number of Events')
            plt.show()


if __name__ == "__main__":
    visualize_logs()
    visualize_logs_counters()
    visualize_logs_screening()
    visualize_logs_gates()
