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


if __name__ == "__main__":
    visualize_logs()
