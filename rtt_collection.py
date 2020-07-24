#!/usr/bin/python3

import threading
import time
import re
import subprocess
import signal
import yaml
import argparse
import os


# Script for starting the rtt collection
# Run locally on a host representing an AS
# Needs to be initiated simultaneously on all machines

# Synchronization parameters -------
# Wait this many seconds until starting the clients.
CLIENT_INIT_DELAY = 2


# Since we want to command with a CLI, we store the intermediate values in files.
NEIGHBORS_FILE='neighbors.txt'
PROCESSES_FILE='processes.txt'
DUMP_FILE='tcp_probe_dump.txt'
IPERF_LOG ="iperf_output.log"

# Commands for CLI
NEIGHBORS_COMMAND = "findtopo"
SENSOR_COMMAND = 'startsensor'
SERVER_COMMAND= 'startserver'
EXPERIMENT_COMMAND='run'
KILL_COMMAND='killall'
CLEAN_COMMAND='clean'
PARSE_COMMAND='parse'

def add_pid_tofile(proc):
    f = open(PROCESSES_FILE + "\n", 'w+')
    f.write(str(proc.pid))  
    f.close()


# Gather neighbors from gen file
def find_neighbors():
    # Parse the gen files.
    # TODO
    print("Parse genfiles to find neighbors...")
    f = open(NEIGHBORS_FILE, 'w')
    f.write("blub. todo")
    f.close()
    return

# Start servers
def start_server():
    print("Starting Server...")
    cmd = "iperf -s -e -i 1"
    proc = subprocess.Popen(cmd)
    add_pid_tofile(proc)
    return


# Start a process that collets srtt with iperf
# Returns the process
def start_srtt_collector(dumpfile):
    cmd = "sudo perf record -e tcp:tcp_probe --filter 'dport == 5002' -o " +  dumpfile
    proc = subprocess.Popen(cmd.split(" "))
    add_pid_tofile(proc)
    return

def start_clients(neighbors):
    client_procs = []
    for neigh_ip in neighbors:
        cmd = "iperf -c " + neigh_ip + " -b 1Mbits -i 1 -t 0 -e"
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        add_pid_tofile(proc)
        client_procs.append(client_procs)
    return client_procs


def sensorstart():
    print("Starting perc to colelct srtt...")
    collector_proc = start_srtt_collector(DUMP_FILE)
    return collector_proc


def run_experiment(runtime=10):
    if(not os.path.exists(NEIGHBORS_FILE)):
        print("Can not start clients. No neighbors file. Run '" + NEIGHBORS_COMMAND + "' first.")
    print("Starting clients..")
    f = open(NEIGHBORS_FILE)
    neighbors = list(f.readlines())
    f.close()
    client_procs = start_clients(neighbors)
    time.sleep(runtime)
    stop_clients(client_procs)

def stop_clients(client_procs):
    # Iperf clients
    print("Stopping Client Processes...")
    f = open(IPERF_LOG)
    for cp in client_procs:
        cp.send_signal(signal.SIGINT)  # send Ctrl-C signal
        stdout, stderr = cp.communicate()
        f.write("Iperf Client: \n")
        f.write(stdout)
        f.write("Errors: \n" + stderr)
    f.close() # TODO: verify that the SIGINT really triggers the program to stop. Last line should be summary print

    # # Server
    # f = open(IPERF_LOG)
    # server_proc.send_signal(signal.SIGINT)  # send Ctrl-C signal
    # stdout, stderr = server_proc.communicate()
    # f.write("Iperf Server: \n")
    # f.write(stdout)
    # f.write("Errors: \n" + stderr)
    # f.close()

def kill():
    print("Killing all Processes...")
    f = open(PROCESSES_FILE)
    pids = list(f.readlines())
    f.close()
    for pid in pids:
        os.system('kill ', pid)

def parse(neighbors, dumploc, datadestination):
    # Parse the dump, create datasets for each destination
    cmd = "sudo perf report --stdio"

def clean():
    kill()
    os.system('rm ', DUMP_FILE)
    os.system('rm ', NEIGHBORS_FILE)
    os.system('rm ', PROCESSES_FILE)

def exec_from_args():
    global parser
    parser = argparse.ArgumentParser()
    FUNCTION_MAP = {'run_all': main,
                    NEIGHBORS_COMMAND: find_neighbors,
                    SENSOR_COMMAND: sensorstart,
                    SERVER_COMMAND: start_server,
                    EXPERIMENT_COMMAND: run_experiment,
                    KILL_COMMAND: kill,
                    CLEAN_COMMAND: clean,
                    PARSE_COMMAND: parse}
    parser.add_argument('command', choices=FUNCTION_MAP.keys())
    #parser.add_argument('t')
    args = parser.parse_args()
    func = FUNCTION_MAP[args.command]
    func()

def main(exp_time):
    clean()
    find_neighbors()
    start_server()
    sensorstart()
    run_experiment(exp_time)

if __name__ == "__main__":
    exec_from_args()
