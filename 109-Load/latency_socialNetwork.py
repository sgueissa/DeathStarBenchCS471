import requests
import json
import subprocess
import time
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

def fetch_traces(jaeger_url, service_name, start_time, end_time):
    print("Start fetching traces")
    all_traces = []
    url = f"{jaeger_url}/api/traces" 
    cur_time = start_time

    while cur_time < end_time:
        params = {
            'service': service_name,
            'start': cur_time,
            'end': int(cur_time + 500000),
            'limit': 1500
        }

        print(requests.Request('GET', url, params=params).prepare().url)
        response = requests.get(url, params=params)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch traces: {response.status_code}, {response.text}")

        if response.headers.get('Content-Type') == 'application/json':
            data = response.json()
            traces = data.get('data', [])
            print(f"Fetched {len(traces)} traces.")
            all_traces.extend(traces)
            cur_time = int(cur_time + 500000)

        else:
            print("Received non-Json response:")
            print(response.text)
            break

    print(f"Fetched {len(all_traces)} traces.")
    print("End fetching traces")

    return all_traces

def run_load():
    commandToRunLoad1 = "../wrk2/wrk -D exp -t 1 -c 32 -d 30s -L -p -s ./wrk2/scripts/social-network/compose-post.lua http://10.89.3.7:8080/wrk2-api/post/compose -R 5000"
    #commandToRunLoad1 = "../wrk2/wrk -D exp -t 1 -c 4 -d 30s -L -p -s ./wrk2/scripts/social-network/compose-post.lua http://localhost:8080/wrk2-api/post/compose -R 500"
    #commandToRunLoad1 = "../wrk2/wrk -D exp -t 1 -c 4 -d 120s -L -p -s ./wrk2/scripts/social-network/compose-post.lua http://10.90.36.43:8080/wrk2-api/post/compose -R 500"

    print("Start running load")

    start_time = int(datetime.now().timestamp() * 1e6) 

    process1 = subprocess.Popen(commandToRunLoad1, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd="../socialNetwork")

    stdout, stderr = process1.communicate()

    end_time = int(datetime.now().timestamp() * 1e6)  

    if process1.returncode != 0:
        print("Error executing command")
        print('STDERR:', stderr.decode())
        exit(1)  # Exit the script with an error code

    print('End running load : \n', stdout.decode())

    return start_time, end_time

def run_load_qos():
    commandToRunLoad1 = "../wrk2/wrk -D exp -t 1 -c 32 -d 300s -L -p -s ./wrk2/scripts/social-network/compose-post.lua http://10.89.3.7:8080/wrk2-api/post/compose -R 5000"
    commandToRunLoad2 = "../wrk2/wrk -D exp -t 1 -c 16 -d 60s -L -p -s ./wrk2/scripts/social-network/compose-post.lua http://10.89.3.7:8080/wrk2-api/post/compose -R 2000"
    #commandToRunLoad1 = "../wrk2/wrk -D exp -t 1 -c 4 -d 300s -L -p -s ./wrk2/scripts/social-network/compose-post.lua http://10.90.36.43:8080/wrk2-api/post/compose -R 500"
    #commandToRunLoad2 = "../wrk2/wrk -D exp -t 1 -c 4 -d 60s -L -p -s ./wrk2/scripts/social-network/compose-post.lua http://10.90.36.43:8080/wrk2-api/post/compose -R 500"

    print("Start running load")

    start_time = int(datetime.now().timestamp() * 1e6) 

    process1 = subprocess.Popen(commandToRunLoad1, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd="../socialNetwork")

    time.sleep(30)

    process2 = subprocess.Popen(commandToRunLoad2, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd="../socialNetwork")

    stdout, stderr = process1.communicate()

    end_time = int(datetime.now().timestamp() * 1e6)  

    if process1.returncode != 0:
        print("Error executing command")
        print('STDERR:', stderr.decode())
        exit(1)  # Exit the script with an error code

    print('End running load : \n', stdout.decode())

    return start_time, end_time


def create_latency_graph(data, tamp):
    spans = []
    for trace in data:
        processes = {process_id: process_info['serviceName'] for process_id, process_info in trace['processes'].items()}
        for span in trace['spans']:
            span_data = {
                "ServiceName": processes.get(span["processID"], "Unknown"),
                "OperationName": span["operationName"],
                "StartTime": span["startTime"] / 1e6,
                "Duration": span["duration"] / 1000.0
            }
            spans.append(span_data)

    df =pd.DataFrame(spans)

    min_start_time = df['StartTime'].min()
    df['StartTime'] -= min_start_time

    grouped_dfs = df.groupby('ServiceName')

    #for service_name, group_df in grouped_dfs:
    #    file_path = f"sn_{service_name}.csv"
    #    group_df.to_csv(file_path, index=False)
    #    print(f"Saved sn_{service_name}.csv")

    n_services = len(grouped_dfs)
    n_cols = 2
    n_rows = (n_services + 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, n_rows * 5))
    axes = axes.flatten()

    for i, (service_name, group_df) in enumerate(grouped_dfs):
        ax = axes[i]
        ax.scatter(group_df['StartTime'], group_df['Duration'])
        ax.set_title(service_name)
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Duration (ms)')

    plt.tight_layout()

    
    filename = f"sn_{tamp}_latency.png"
    plt.savefig(filename)

def create_tail_latency_graph(tamp):
    col_name = ["tail_latency"]
    df = pd.read_fwf('../socialNetwork/u', names=col_name)
    df.insert(0, 'time', range(0, 0 + len(df)))
    # Replace any character that is not a digit or period with an empty string
    df['tail_latency'] = df['tail_latency'].astype(str).str.replace(r'[^\d.]', '', regex=True)

    # Convert the cleaned strings back to numeric type, use errors='coerce' to handle any remaining non-numeric entries
    df['tail_latency'] = pd.to_numeric(df['tail_latency'], errors='coerce').dropna()
    df['tail_latency'] = (df['tail_latency'] / 1000).round(2)
    df['time'] = (df['time'] / 10).round(1)

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(df['time'], df['tail_latency'], marker='o')
    plt.xlabel('Time (s)')
    plt.ylabel('Average Latency (ms)')
    plt.title('99th Percentile Tail Latency')
    plt.yscale("log")
    
    plt.grid(True)
    filename = f"sn_{tamp}_tail_latency.png"
    plt.savefig(filename, format='png', dpi=300)

def main():
    #jaeger_url = 'http://localhost:16686'
    #jaeger_url = 'http://10.90.36.43:16686'
    jaeger_url = 'http://10.89.3.7:16686'
    service_name = 'nginx-web-server'
    #commandToStartDocker = "./start_socialnetwork"

    #process = subprocess.Popen(commandToStartDocker, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #stdout, stderr = process.communicate()

    #if process.returncode != 0:
    #    print("Error executing command")
    #    print('STDERR:', stderr.decode())
    #    exit(1)  # Exit the script with an error code

    start_time, end_time = run_load_qos()

    traces = fetch_traces(jaeger_url, service_name, start_time, end_time)

    tamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    create_latency_graph(traces, tamp)
    create_tail_latency_graph(tamp)
    
if __name__ == '__main__':
    main()

