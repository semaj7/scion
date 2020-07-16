#!/bin/python3

import threading
import time
import re
import subprocess
import signal
import yaml

# Script for starting the rtt collection
# Run locally on a host representing an AS
# Needs to be initiated simultaneously on all machines

# Synchronization parameters -------
# Wait this many seconds until starting the clients.
CLIENT_INIT_DELAY = 2

# Gather neighbors from gen file
def find_neighbors():
    # Parse the gen files.
    # TODO
    return [""]

# Start servers
def start_server():
    cmd = "iperf -s -e -i 1"
    return subprocess.Popen(cmd)


# Start a process that collets srtt with iperf
# Returns the process
def start_srtt_collector():
    cmd = "sudo perf record -e tcp:tcp_probe --filter 'dport == 5002' "
    return subprocess.Popen(cmd)

def start_clients(neighbors):
    for neigh_ip in neighbors:
        cmd = "iperf -c " + neigh_ip + " -b 1Mbits -i 1 -t 0 -e"
        return subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)

def init():
    print("Initializing...")
    neighbors = find_neighbors()
    start_server()
    print("Ready.")
    return neighbors

def run(neighbors, dumpname):
    print("Starting proc.")
    collector_proc = start_srtt_collector(dumpname)
    print("Starting clients.")
    client_procs = start_clients(neighbors)
    return collector_proc, client_procs

def stop(collector_proc, client_procs, server_proc):

    # Iperf clients
    print("Killing Processes...")
    f = open("iperf_output.log")
    for cp in client_procs:
        cp.send_signal(signal.SIGINT)  # send Ctrl-C signal
        stdout, stderr = cp.communicate()
        f.write("Iperf Client: \n")
        f.write(stdout)
        f.write("Errors: \n" + stderr)
    f.close() # TODO: verify that the SIGINT really triggers the program to stop. Last line should be summary print

    # Collector
    collector_proc.send_signal(signal.SIGINT)  # send Ctrl-C signal

    # Server
    f = open("iperf_server_output.log")
    server_proc.send_signal(signal.SIGINT)  # send Ctrl-C signal
    stdout, stderr = server_proc.communicate()
    f.write("Iperf Client: \n")
    f.write(stdout)
    f.write("Errors: \n" + stderr)
    f.close()

def parse(neighbors, dumploc, datadestination):
    # Parse the dump, create datasets for each destination
    cmd = "sudo perf report --stdio"

def main():
    dumpname = 'tcp_probe.data'
    server_proc, neighbors = init()
    collector_proc, client_procs = run(neighbors, dumpname)
    stop(collector_proc, client_procs, server_proc)
    parse(neighbors, dumpname)

