#!/usr/bin/python3

import threading
import time
import re
import subprocess
import signal
import yaml
import argparse
import os
import json

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
RUN_ALL_COMMAND = "runall"
NEIGHBORS_COMMAND = "findtopo"
SENSOR_COMMAND = 'startsensor'
SERVER_COMMAND= 'startserver'
EXPERIMENT_COMMAND='run'
KILL_COMMAND='killall'
CLEAN_COMMAND='clean'
PARSE_COMMAND='parse'

def add_pid_tofile(proc):
    f = open(PROCESSES_FILE, 'w+')
    f.write(str(proc.pid) + "\n")
    f.close()

# Gather neighbors from gen file
# Store into NEIGHBORFILE. Structure:       neighborAS,PublicOverlayIP,RemoteOverlayIP
# TODO: since we are not 100% sure what the genfile in SCIONLab will look like, this might fail.
# TODO:         if there are AS folders that do not belong to the AS, we need another configuration parameter
#               that is checked against the folders we find in gen/
def find_neighbors():
    # Parse the gen files.
    genfile = "gen/"
    topofiles = []
    for dirName, _, fileList in os.walk(genfile):
        for f in fileList:
            if f == "topology.json":
                filepath = dirName+"/"+f
                if re.fullmatch(r'gen/ISD\d+/AS.+/br\d+-.+/topology.json', filepath):
                    print(filepath)
                    topofiles.append(filepath)

    # Checks #
    ases = set()
    isds = set()
    brs = set()
    for p in topofiles:
        _, isd, asid, br, _ = p.split("/")
        ases.add(asid)
        isds.add(isd)
        brs.add(br)
    if len(ases) != 1:
        print("WARNING: The number of AS folders is unexpected: ", ases)
    if len(isds) != 1:
        print("WARNING: The number of ISD folders is unexpected: ", isds)
    num_brs = len(brs)

    # Since the topofiles in the different br folders are redundant (at least as far as we experienced), it is
        # enough to just take one topofile.
    topofile = topofiles[0]

    # traverse the json config file
    neighbors = []
    with open(topofile) as f:
        topo = json.load(f)

    if num_brs != len(topo['BorderRouters']):
        print("WARNING: the number of border router folders is not identical to the number of border router entries"
              " in the topology.json file: in json: ", len(topo['BorderRouters']), " folders: ", brs)

    for br_props in topo['BorderRouters']:
        ifs_config = topo['BorderRouters'][br_props]["Interfaces"]
        for ifs in ifs_config:
            interface = ifs_config[ifs]
            props = {'ISD_AS': interface['ISD_AS'], 'Public': interface['PublicOverlay']['Addr'],
                     'Remote': interface['RemoteOverlay']['Addr']}
            neighbors.append(props)
    print("Parse genfiles to find neighbors...")
    f = open(NEIGHBORS_FILE, 'w')
    for neigh in neighbors:
        f.write(",".join(list(neigh.values())) + "\n")
    f.close()
    return

# Start servers
def start_server():
    print("Starting Server...")
    cmd = "iperf -s -e -i 1"
    proc = subprocess.Popen(cmd, preexec_fn=os.setsid)
    add_pid_tofile(proc)
    return


# Start a process that collets srtt with iperf
# Returns the process
# TODO: testing and debugging
def start_srtt_collector(dumpfile):
    cmd = "sudo perf record -e tcp:tcp_probe --filter 'dport == 5002' -o " +  dumpfile
    proc = subprocess.Popen(cmd.split(" "))
    add_pid_tofile(proc)
    return

# Starts the clients with a fixed experiment length.
# TODO: parametrize the experiment length. Use a config file, preferably the same as with the rest of experiments
def start_clients(neighbors):
    client_procs = []
    client_files = []
    i = 0
    for neigh_line in neighbors:
        i += 1
        if neigh_line == "":
            continue

        asname, publicip, remoteip = neigh_line.split(",")
        neigh_ip = publicip # TODO: see if this is true

        # Use this one with the port specification for local testing (when IP is the same)
        #cmd = "/usr/bin/iperf -c " + neigh_ip + " -p " + str(5000 + i) +  " -b 1Mbits -i 1 -t 0 -e"

        cmd = "/usr/bin/iperf -c " + neigh_ip +  " -b 1Mbits -i 1 -t 0 -e"

        f = open("iperf_client" + str(i) + ".log", 'w')
        print("Execute: ", cmd.split())
        proc = subprocess.Popen(cmd.split(), stdout=f, preexec_fn=os.setsid)
        add_pid_tofile(proc)
        client_procs.append(proc)
    return client_procs, client_files

def sensorstart():
    # TODO no testing done yet.
    print("Starting perc to colelct srtt...")
    collector_proc = start_srtt_collector(DUMP_FILE)
    return collector_proc


def run_experiment(runtime=10):
    if(not os.path.exists(NEIGHBORS_FILE)):
        print("Can not start clients. No neighbors file. Run '" + NEIGHBORS_COMMAND + "' first.")
    print("Starting clients..")
    f = open(NEIGHBORS_FILE)
    neighbors = list(f.read().split("\n"))
    f.close()
    print("Neighbors: ", neighbors)
    client_procs, client_files = start_clients(neighbors)
    time.sleep(runtime)
    stop_clients(client_procs, client_files)

def stop_clients(client_procs, client_files):
    # Iperf clients
    print("Stopping Client Processes...")
    for cp in client_procs:
        os.killpg(os.getpgid(cp.pid), signal.SIGTERM)

    for f in client_files:
        f.close()

    # f = open(IPERF_LOG, 'w')
    # f.close() # TODO: verify that the SIGINT really triggers the program to stop. Last line should be summary print

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
    # TODO
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
    FUNCTION_MAP = {RUN_ALL_COMMAND: run_all,
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

def run_all(exp_time):
    clean()
    find_neighbors()
    start_server()
    sensorstart()
    run_experiment(exp_time)

if __name__ == "__main__":
    exec_from_args()
