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
            'end': int(cur_time + 499999),
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
    commandToRunLoad1 = "../wrk2/wrk -D exp -t 6 -c 200 -d 30s -L -s ./wrk2/scripts/media-microservices/compose-review.lua http://10.90.36.43:8080/wrk2-api/review/compose -R 1000"

    print("Start running load")

    start_time = int(datetime.now().timestamp() * 1e6) 

    process1 = subprocess.Popen(commandToRunLoad1, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd="../DeathStarBench/mediaMicroservices")

    stdout, stderr = process1.communicate()

    end_time = int(datetime.now().timestamp() * 1e6)  

    if process1.returncode != 0:
        print("Error executing command")
        print('STDERR:', stderr.decode())
        exit(1)  # Exit the script with an error code

    print('End running load : \n', stdout.decode())

    return start_time, end_time

def run_load_qos():
    commandToRunLoad1 = "../wrk2/wrk -D exp -t 6 -c 200 -d 120s -L -p -s ./wrk2/scripts/social-network/compose-post.lua http://10.90.36.43:8080/wrk2-api/post/compose -R 1000"
    commandToRunLoad2 = "../wrk2/wrk -D exp -t 6 -c 200 -d 30s -L -p -s ./wrk2/scripts/social-network/compose-post.lua http://10.90.36.43:8080/wrk2-api/post/compose -R 1000"

    print("Start running load")

    start_time = int(datetime.now().timestamp() * 1e6) 

    process1 = subprocess.Popen(commandToRunLoad1, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd="../DeathStarBench/socialNetwork")

    time.sleep(30)

    process2 = subprocess.Popen(commandToRunLoad2, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd="../DeathStarBench/socialNetwork")

    stdout, stderr = process2.communicate()

    end_time = int(datetime.now().timestamp() * 1e6)  

    if process2.returncode != 0:
        print("Error executing command")
        print('STDERR:', stderr.decode())
        exit(1)  # Exit the script with an error code

    subprocess.Popen("cp s s1", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd="../DeathStarBench")

    stdout, stderr = process1.communicate()

    end_time = int(datetime.now().timestamp() * 1e6)  

    if process1.returncode != 0:
        print("Error executing command")
        print('STDERR:', stderr.decode())
        exit(1)  # Exit the script with an error code

    print('End running load : \n', stdout.decode())

    return start_time, end_time


def create_graphes(data):
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

    for service_name, group_df in grouped_dfs:
        file_path = f"ms_{service_name}.csv"
        group_df.to_csv(file_path, index=False)
        print(f"Saved ms_{service_name}.csv")

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
    plt.savefig('ms_graph.png')
    
    return pd.DataFrame(spans)

def main():
    jaeger_url = 'http://10.90.36.43:16686'
    service_name = 'nginx'
    commandToStartDocker = "./start_mediaService"

    #process = subprocess.Popen(commandToStartDocker, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #stdout, stderr = process.communicate()

    #if process.returncode != 0:
    #    print("Error executing command")
    #    print('STDERR:', stderr.decode())
    #    exit(1)  # Exit the script with an error code

    start_time, end_time = run_load()

    traces = fetch_traces(jaeger_url, service_name, start_time, end_time)

    df_traces = create_graphes(traces)
    
if __name__ == '__main__':
    main()

