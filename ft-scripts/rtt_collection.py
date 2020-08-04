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
import numpy as np
from ftutils import load_config

# Script for starting the rtt collection
# Run locally on a host representing an AS
# Needs to be initiated simultaneously on all machines

# Synchronization parameters -------
# Wait this many seconds until starting the clients.
CLIENT_INIT_DELAY = 2

# Commands for CLI
RUN_ALL_COMMAND = "runall"
NEIGHBORS_COMMAND = "topo"
SENSOR_COMMAND = 'sensor'
SERVER_COMMAND= 'server'
EXPERIMENT_COMMAND='run'
KILL_COMMAND='kill'
CLEAN_COMMAND='cleanall'
PROCESS_COMMAND='preprocess'
PARSE_COMMAND='parse'

def add_pid_tofile(proc):
    f = open(config['processes_file'], 'a+')
    print("Adding ", str(proc.pid), " to the file.")
    f.write(str(proc.pid) + "\n")
    f.close()

# Gather neighbors from gen file
# Store into NEIGHBORFILE. Structure:       neighborAS,PublicOverlayIP,RemoteOverlayIP
def find_neighbors():
    # Parse the gen files.
    topofiles = []
    if not os.path.exists(config['genfolder']):
        print("ERROR: When parsing neighbors, genfolder does not exist.")
        return
    for dirName, _, fileList in os.walk(config['genfolder']):
        for f in fileList:
            if f == "topology.json":
                filepath = dirName+"/"+f

                # Since our machine is an endhost, it's in an endhost folder. this may change from machine to machine.
                if re.fullmatch(r'.+gen/ISD\d+/AS.+/endhost/topology.json', filepath):
                    print(filepath)
                    topofiles.append(filepath)

    # Checks #
    ases = set()
    isds = set()
    brs = set()
    for p in topofiles:
        spl =  p.split("/")
        isd = spl[-3]
        asid = spl[-2]
        br = spl[-1]
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
    f = open(config['neighbors_file'], 'w')
    for neigh in neighbors:
        f.write(",".join(list(neigh.values())) + "\n")
    f.close()
    return

# Start servers
def start_server():
    print("Starting Server...")
    # if not os.path.exists(IP_ADDR_FILE):
    #     print("ERROR: LOCAL IP FILE ", IP_ADDR_FILE, 'is missing.')
    #     return
    # f = open(IP_ADDR_FILE, 'r')
    # ip = list(f.readlines())
    # f.close()
    #cmd = "iperf -s -e -i 1 -B " + ip[0]
    cmd = "iperf -s -e -i 1"

    proc = subprocess.Popen(cmd, preexec_fn=os.setsid, shell=True)
    add_pid_tofile(proc)
    return

# Start a process that collets srtt with iperf
# Returns the process
# TODO: fix precision problem: timestamp resolution too big and also number of packets are too small
def start_srtt_collector():
    cmd = "sudo perf record -e tcp:tcp_probe -o " +  config['perf_record_file'] +  " -T"# --filter dport==5002"
    proc = subprocess.Popen(cmd.split(" "), preexec_fn=os.setsid)
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
    print("Starting perf to collect srtt...")
    collector_proc = start_srtt_collector()
    return collector_proc

def run_experiment():
    if config['local_test']:
        neighbors = ['LOCALTEST,127.0.0.1,127.0.0.1']
    else:
        if(not os.path.exists(config['neighbors_file'])):
            print("ERROR: Can not start clients. No neighbors file. Run '" + NEIGHBORS_COMMAND + "' first.")
            return
        print("Starting clients..")
        f = open(config['neighbors_file'])
        neighbors = list(f.read().split("\n"))
        f.close()
    print("Neighbors: ", neighbors)
    client_procs, client_files = start_clients(neighbors)
    time.sleep(config['rtt_experiment_time'])
    stop_clients(client_procs, client_files)

def stop_clients(client_procs, client_files):
    # Iperf clients
    print("Stopping Client Processes...")
    for cp in client_procs:
        os.killpg(os.getpgid(cp.pid), signal.SIGTERM)

    for f in client_files:
        f.close()

# TODO: This is probably not very safe yet, Anyone could change the pid file.
def kill_all():
    if (not os.path.exists(config['processes_file'])):
        print("No Process file stored. Nothing to kill.")
        return
    print("Killing all Processes...")
    f = open(config['processes_file'], 'r')
    pids = list(f.readlines())
    f.close()
    for pid in pids:
        print("Killing ", str(pid))
        os.system('sudo kill ' + pid)
    os.system("pkill iperf")
    os.system("pkill perf")

# Preprocess results, from record format to report
def preprocess():
    # Parse the dump, create datasets for each destination
    print("Preprocessing perf dump with 'perf report'.")
    cmd = "sudo perf report --stdio -i " + config['perf_record_file'] + " -F time,sample,trace --header > " + config['perf_dump_file']
    os.system(cmd)
    print("Preprocessing done.")

# Parse and merge perf dump
# Store in csv file.
# Fields: timestamp, sample, traces (explicitly)
# Examples:
#   26352.200000             3  src=127.0.0.17:5001 dest=127.0.0.1:52378 mark=0 data_len=32741 snd_nxt=0x854cd811
#           snd_una=0x854cd811 snd_cwnd=10 ssthresh=2147483647 snd_wnd=65536 srtt=16 rcv_wnd=65483 sock_cookie=bf
#   26352.200000             3  src=127.0.0.19:5001 dest=127.0.0.1:47808 mark=0 data_len=32741 snd_nxt=0x88f83940
#           snd_una=0x88f83940 snd_cwnd=10 ssthresh=2147483647 snd_wnd=65536 srtt=12 rcv_wnd=65483 sock_cookie=c1
def parse_results():
    # timestamp, sample, traces
    data = []
    data.append(['timestamp', 'num_samples', 'source', 'dest', 'data_len', 'srtt'])

    print("Parsing datafile " + config['perf_dump_file'] + "...")

    wcOutput = str(subprocess.check_output(("wc -l " + config['perf_dump_file']).split()))
    filelength = int(re.match(r'b\'(\d+).+', wcOutput).group(1))
    linecounter = 0

    with open(config['perf_dump_file'], 'r') as df:
        linestring = '_'
        while (linestring):


            # Show progress
            if linecounter % 100000 == 0:
                print("Read %d / %d lines." % (linecounter, filelength), end="\r")

            # Perf header contains #
            if linestring[0] == '#':
                linestring = df.readline()
                linecounter += 1
                continue

            matchstring = r'(\s*\d+\.\d+)\s+(\d+)\s+src=(\S+)\s+dest=(\S+).+data_len=(\d+).+srtt=(\d+).+'
            matchstring = r'.*\d+.*'
            r'gen/ISD\d+/AS.+/br\d+-.+/topology.json'
            match = re.match(r'.*(\d+\.\d+)\s+(\d+)\s+src=(\S+)\s+dest=(\S+).*data_len=(\d+).*srtt=(\d+).*', linestring)
            #match = re.match(r'.*(\d+\.\d+).*', linestring)

            if match:
                print(match.groups())
                timestamp, num_samples, source, dest, data_len, srtt = match.groups()
                line = [timestamp, num_samples, source, dest, data_len, srtt]
                data.append(line)
            elif linestring != "":
                print("FAIL when parsing the following line: ", linestring)

            linestring = df.readline()
            linecounter += 1

        print("Read all %d lines.                     " % (filelength))

    # Write compressed data to a csv file
    np.savetxt(config['parsed_destination'], np.array(data), delimiter=",", fmt='%s')
    print("Saving parsed file in ", config['parsed_destination'])

def clean():
    kill_all()
    os.system('rm ' + config['perf_record_file'])
    os.system('rm ' +  config['neighbors_file'])
    os.system('rm ' +  config['processes_file'])
    #os.system('rm ' + config['perf_dump_file'])


def exec_from_args():
    #global parser
    parser = argparse.ArgumentParser()
    FUNCTION_MAP = {RUN_ALL_COMMAND: run_all,
                    NEIGHBORS_COMMAND: find_neighbors,
                    SENSOR_COMMAND: sensorstart,
                    SERVER_COMMAND: start_server,
                    EXPERIMENT_COMMAND: run_experiment,
                    KILL_COMMAND: kill_all,
                    CLEAN_COMMAND: clean,
                    PROCESS_COMMAND: preprocess,
                    PARSE_COMMAND: parse_results}
    parser.add_argument('command', choices=FUNCTION_MAP.keys())
    #parser.add_argument('-t', action="store", dest="exptime", type=int, default=10)

    args = parser.parse_args()
    # global exp_time
    # exp_time = args.exptime
    func = FUNCTION_MAP[args.command]
    func()

def run_all(pass_config=None):
    if pass_config:
        global config
        config = pass_config
    clean()
    find_neighbors()
    start_server()
    time.sleep(2)
    sensorstart()
    time.sleep(2)
    run_experiment()
    time.sleep(2)
    kill_all()
     # Don't know why, but somehow it needs killing twice.
    time.sleep(2)
    preprocess()
    clean()
    parse_results()




if __name__ == "__main__":
    global config
    config = load_config('ft-scripts/config-defaults.yaml')
    # Note: there is more config on the top of this file
    exec_from_args()
