import os
import random
import sys

import matplotlib.pyplot as plt
import pandas as pd


def read_files_from_dir(_input_dir, file_suffix):
    for filename in os.listdir(_input_dir):
        if file_suffix in filename:
            yield filename


def write_to_csv(output_file, header, rows):
    with open(output_file, 'w') as file:
        file.write(header)
        for row in rows:
            file.write(','.join(map(str, row)) + '\n')


def extract_metrics_from_file(_input_dir, filename, process_map):
    process_name, pid = filename.split('_')[0:2]
    process_map[process_name] = process_map.get(process_name, 0) + 1

    with open(os.path.join(_input_dir, filename), 'r') as file:
        lines = file.readlines()

    pid_line = " Performance counter stats for process id '" + pid + "':\n"
    if pid_line not in lines:
        print(f"Error: {filename} does not contain performance counter stats")
        return None

    useful_lines = lines[lines.index(pid_line) + 2:]
    return [process_name, pid, process_map[process_name]] + [line.split()[0] for line in useful_lines[:3]]


def aggregate_CPU_metrics(_input_dir, output_file):
    output_file += ".csv"
    header = "Process name, PID, instance #, # instructions, # cycles, # i-cache misses\n"
    process_map = {}
    rows = [extract_metrics_from_file(_input_dir, filename, process_map)
            for filename in read_files_from_dir(_input_dir, "CPU.out") if
            extract_metrics_from_file(_input_dir, filename, process_map) is not None]

    write_to_csv(output_file, header, rows)
    return output_file


def aggregate_topdown_metrics(_input_dir, output_file):
    output_file += "_topdown.csv"
    header = "Process ID, Retiring, Bad Speculation, Frontend Bound, Backend Bound\n"
    rows = []

    for filename in read_files_from_dir(_input_dir, "topdown.out"):
        with open(os.path.join(_input_dir, filename), 'r') as file:
            lines = file.readlines()

        # Finding the line with process ID
        for i, line in enumerate(lines):
            if "Performance counter stats for process id" in line:
                pid = line.split("'")[1]  # Extracting the process ID
                # Assuming the metrics are in the line immediately after the next line
                metrics_line = lines[i + 3]
                metrics = metrics_line.split()
                # Extracting only the required metrics
                retiring, bad_spec, frontend_bound, backend_bound = metrics[0], metrics[1], metrics[2], metrics[3]
                # TODO remove this /Done
                # pid = random.randint(0, 100)

                rows.append([pid, retiring, bad_spec, frontend_bound, backend_bound])
                break  # Assuming one set of metrics per file

    write_to_csv(output_file, header, rows)


def sort_db(file):
    df = pd.read_csv(file)
    df = df[df[' # instructions'].str.contains('<not') == False]
    df.sort_values(by=['Process name', ' instance #'], inplace=True)
    df.to_csv(file, index=False)


def plot_baton_graph(file):
    try:
        df = pd.read_csv(file)
        df['IPC'] = pd.to_numeric(df[' # instructions'], errors='coerce') / pd.to_numeric(df[' # cycles'],
                                                                                          errors='coerce')
        df['MPKI'] = pd.to_numeric(df[' # i-cache misses'], errors='coerce') / pd.to_numeric(df[' # instructions'],
                                                                                             errors='coerce') * 1000
        df = df.groupby('Process name').mean()

        for metric in ['IPC', 'MPKI']:
            plt.figure(figsize=(8, 6))
            df[metric].plot.bar(rot=90)
            plt.xlabel("Process Name")
            plt.ylabel(metric)
            plt.title(f"{metric} Baton Graph")
            plt.tight_layout()
            plt.savefig(f"{metric.lower()}_baton_graph.png")

    except Exception as e:
        print(f"An error occurred: {e}")


def plot_baton_graph_topdown(file):
    try:
        # Reading the CSV file
        df = pd.read_csv(file)

        # Convert percentage strings to float
        for col in [' Retiring', ' Bad Speculation', ' Frontend Bound', ' Backend Bound']:
            df[col] = df[col].str.rstrip('%').astype('float') / 100

        # Plotting
        fig, ax = plt.subplots(figsize=(8, 6))
        colors = ['#3498db', '#e74c3c', '#2ecc71', '#f1c40f']
        bottom = [0] * len(df)

        for idx, col in enumerate([' Frontend Bound', ' Bad Speculation', ' Backend Bound', ' Retiring']):
            ax.bar(df['Process ID'], df[col], bottom=bottom, label=col, color=colors[idx])
            bottom = [bottom[i] + df[col].iloc[i] for i in range(len(df))]

        ax.set_xlabel('Process ID')
        ax.set_ylabel('Metrics')
        ax.set_title('Topdown Metrics Baton Graph')
        plt.xticks(rotation=90)
        ax.legend()
        plt.tight_layout()
        plt.savefig("topdown_metrics_baton_graph.png")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == '__main__':
    input_dir, base_output_file = sys.argv[1], sys.argv[2]
    cpu_csv = aggregate_CPU_metrics(input_dir, base_output_file)
    sort_db(cpu_csv)
    plot_baton_graph(cpu_csv)
    aggregate_topdown_metrics(input_dir, base_output_file)
    plot_baton_graph_topdown(base_output_file + "_topdown.csv")
