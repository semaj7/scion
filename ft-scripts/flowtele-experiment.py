#!/usr/bin/python3.7

#!/usr/bin/python



# WARNING: If you use parts of this directly over python, not using the command line with args,
#       you might require a custom function, since almost all functions expect the following code to be run beforehand:
#               global config
#               config = setup_configuration()
#               infer_config()


# Typical Use:

# paths:        finds paths from sender to receivers
# calibrate:    starts calibrator flows, one per path, to determine fair shares across paths

# listen:        starts listeners on receivers
#               start tshark? %todo, not clear yet

#
# setup:        start fshaper on sender
#               starts athena on sender
#               starts tshark everywhere

# start:        starts flows from sender to receiver through selected paths

# kill:         stop all programs

from functools import partial
import subprocess
import re
import sys
import time
import math
import subprocess
import os
import threading
from datetime import datetime
import yaml
from collections import Counter
import random
import signal
from rtt_collection import run_all as rtt_run
import argparse
from ftutils import *

# Checks if the current host belongs to roles that should perform this command.
# Returns 'true' if should skip
# Also prints suitable messages
def skip_this_command(advancing_roles):
    this_role = config['this_role']
    if this_role in advancing_roles:
        print("This machine has role ", this_role, ". Will perform this command.")
        return False
    else:
        print("This machine has role ", this_role, ". Will skip this command.")
        return True

# Necessary to be executed at some point.
def infer_config():
    hostname = os.uname()[1]
    config['this_hostname'] = hostname
    label = config['hostname_label_map'][hostname]
    config['this_label'] = label
    role = config['label_role_map'][label]
    config['this_role'] = role

    # Create Result Directory
    resultFilePrefix = generateResultDir(config['name'])  # save it as: 'result_dir' config
    config['result_dir'] = resultFilePrefix

    # Infer Filelocations
    config['neighbors_file'] = config['result_dir'] + config['neighbors_file']
    config['processes_file'] = config['result_dir'] + config['processes_file']
    config['perf_record_file'] = config['result_dir'] + 'hostdata/' + config['perf_record_file']
    config['perf_dump_file'] = config['result_dir'] + 'hostdata/' + config['perf_dump_file']
    config['parsed_destination'] = config['result_dir'] + 'condensed/' + config['parsed_destination']
    config['iperf_log'] = config['result_dir'] + 'hostlogs/' + config['iperf_log']

    # Dump Config
    f = open(resultFilePrefix + 'config.yaml', 'w')
    yaml.dump(config, f)
    f.close()


# If an explicit config is passed, will ignore any CLI arguments
def setup_configuration(explicit_config=None):
    global config
    if explicit_config is None:
        # Load Default Config
        config = load_config("ft-scripts/config-defaults.yaml")
            # Load Arguments
            #setLogLevel(config['scion_log_level'])
            # if len(sys.argv) > 1:
            #     parse_args(config)
            # else:
            #     print("No options provided. Will execute default experiment.")
    else:
        config = explicit_config
        print("Loaded an explicit config.")

    return config

def initiateLog():
    hostlogfile = config['result_dir']+"hostlogs/%s.log" % config['this_label']
    config['hostlog'] = hostlogfile
    if os.path.exists(hostlogfile):
        print("WARNING: this eperiment named '" +  config['name'] +  "' has already been run.")
        answer = input("Continue? ('y' for yes)")
        if answer != "y" and answer != 'yes':
            print("Not answered with 'y'. Abort.")
            return
    print("Create log at ", hostlogfile)
    with open(hostlogfile, 'w') as logfile:
        logfile.write(("%.6f" % time.time())+": "+config['this_label']+": Started\n")

def log(logContent):
    hostlogfile = config['hostlog']
    with open(hostlogfile, "a+") as logfile:
        logfile.write(("%.6f" % time.time())+": "+config['this_label']+": "+logContent+"\n")



# If print_to_console, then outfile is ignored. This is therefore only used for debugging.
def execute(commandstring, outfile, setsid=False, env=None, print_to_console=False):
    print("Executing: ", commandstring)
    if not print_to_console:

    # TODO: having both '>' and 'stdout=' seems odd.
        commandstring += " > " + outfile
        with open(outfile, 'w') as outfile:
            proc = subprocess.Popen(commandstring.split(), preexec_fn=os.setsid if setsid else None, env=env,
                                    stderr=outfile, stdout=outfile)
    else:
        proc = subprocess.Popen(commandstring.split(), preexec_fn=os.setsid if setsid else None, env=env)
    return proc




#####################################################################################


def startTshark():
    fileoutput = config['result_dir']+'hostdata/'+config['this_label']+ config['tshark_suffix']
    tcpDumpCommmand = ('tshark -i '+ config['tshark_net_interface'] + " -Y 'scion.udp.dstport==40002'")
    tcpDumpCommmand = ('tshark -i '+ config['tshark_net_interface'])
    execute(fileoutput, fileoutput, False, None, False)
    print("Started tshark.")

def start_fshaper():
    random.seed(config['this_hostname']) # Unsure if/why needed
    fshaperlog = config['result_dir'] + "hostlogs/" + config['this_label'] + config['fshaper_suffix']
    command = config['ftsocket_location'] + " --fshaper-only"
    print_to_console = config['print_to_console']
    proc = execute(command, fshaperlog, True, None, print_to_console)

# Start iperf server with TCP on destination hosts
def start_listener(num=2, scion=True):
    print("Starting Quic Listener...")

    local_ip = config['hosts']['this_hostname']['ip']
    local_ia = config['hosts']['this_hostname']['ia']

    command = config['quic_listener_location']
    if scion:
        command = " --scion"

    # TODO: unsure how to treat NUM
    command += "--local-ia %s --ip %s --num %s" % (local_ia, local_ip, num)

    resfile = config['result_dir'] + "hostlogs/" + config['this_label'] + config['quicrecv_suffix']
    print_to_console = config['print_to_console']
    execute(command, resfile, True, None, print_to_console)

    print("Quic Listener Started.")
    # time.sleep(config['receiver_duration'])
    # os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    # fout.close()

    return

# Directly invoked from CLI
def kill():
    print("Killing all flowtele programs...")
    os.system("sudo pkill tshark")
    os.system("sudo pkill flowtele_listener")
    os.system("sudo pkill flowtele_socket")
    os.system("sudo pkill athena")
    return


def run_quicnative_experiment():
    # Start Clients
    time.sleep(config['send_duration'])
    print("Sending for ", config['send_duration'] + " seconds..")
    # Stop Clients
    return

def run_scion_experiment(receivers):

    for recv in receivers:

        # Read calibrator results

        # Choose the path
        # TODO: simplest heuristic, works well if only one receiver:
        #           just choose path that showed the biggest throughput in calibration phase. use it for all flows
        best_path = 12345

    # Start Clients
    procs = []
    for flownum in range(config['num_flows']):
        proc = start_scion_flow(best_path, recv, flownum)
        procs.append(proc)


    time.sleep(config['send_duration'])
    print("Sending for ", config['send_duration'] + " seconds..")

    # Stop Clients
    for proc in procs:
        proc.kill()
    print("Sending finished.")

# Directly invoked from CLI
def run_ft_experiment():
    print("Running the Main Flowtele Experiment..")
    admitted_roles = ['sender', 'tester']
    if skip_this_command(admitted_roles):
        time.sleep(config['send_duration'])
        return

    if config['use_scion']:
        run_scion_experiment()
    else:
        run_quicnative_experiment()

    print("Sending over: ", time.time())

# Directly invoked from CLI
def start_listeners():
    print("Starting the listeners")
    startTshark()
    if skip_this_command(["receiver", 'tester']):
        print("Delaying for Listener to prepare...")
        time.sleep(config['sender_delay_time'])
        return
    start_listener()

# Directly invoked from CLI
def setup_sender():
    print("Setting up Sender")

    if skip_this_command(["sender", 'tester']):
        return
    if config['use_shaping']:
        start_fshaper()
        start_athena()


def get_path(remote_name):
    print("Getting paths for ", remote_name)
    local_ia = config['hosts'][config['this_hostname']]['ia']
    ftsocket_exec = config['ftsocket_location']
    remote_ia = config['hosts'][remote_name]['ia']
    command =  ftsocket_exec + " --mode fetch --local-ia " + local_ia + " --remote-ia " + remote_ia
    remote_label = config['hostname_label_map'][remote_name]
    outname = "paths_" + remote_label + ".txt"
    execute(command, outname, False, None, False)
    numpaths = str(subprocess.run(("wc -l " + outname).split(), capture_output=True).stdout).split(" ")[0]

    print("Number of paths found: ", numpaths)

# Directly invoked from CLI
# Can be executed on every machine. Will act according to role.
def get_paths():
    print("Getting Paths:")
    admitted_roles = ['sender', 'tester']
    if skip_this_command(admitted_roles):
        return

    receivers = load_all_hostnames(config, filter_roles=['receiver'])
    for recv in receivers:
        get_path(recv)

# Start a quic flow through scion over the given path to the recv-name.
# Each flow needs a dbusnum that identifies it in the shaper.
def start_scion_flow(path, recv_hostname, dbusnum, additional_suffix=""):

    print("Starting Flow to host ", recv_hostname, " through path ", path)
    thishostname = config['this_hostname']
    ft_send = config['ftsocket_location']
    recv_ip = config['hosts'][recv_hostname]['ip']
    recv_ia = config['hosts'][recv_hostname]['ia']
    local_ip = config['hosts'][thishostname]['ip']
    local_ia = config['hosts'][thishostname]['ia']
    local_port = config['local_port_start_range'] + dbusnum
    port = config['listener_port']

    cmd = ft_send
    cmd += " --quic-sender-only --scion --local-ip %s --ip %s --local-ia %s -ia %s" % (local_ip, recv_ip, local_ia, recv_ia)
    cmd += " --path '%s' --loacl-port %s --port %s --quic-dbus-index %s" % (path, local_port, port, dbusnum)

    outfile = config['result_dir'] + "hostlogs/" + config['this_label'] + "_" + dbusnum + "_" \
              + additional_suffix + config['flow_suffix']

    execute(cmd, outfile, False, None, True)
    proc = subprocess.Popen(cmd.split(), preexec_fn=os.setsid)
    return proc


# Start a quic flow through regular internet to reciever
# Each flow needs a dbusnum that identifies it in the shaper.
 # TODO, unfinished, not thought through

def start_quic_flow(recv_hostname, dbusnum, additional_suffix=""):
    print("Starting Flow to host ", recv_hostname, " through path ", path)

    ft_send = config['ftsocket_location']
    recv_ip = config['hosts'][recv_hostname]['ip']
    recv_ia = config['hosts'][recv_hostname]['ia']
    local_ip = config['hosts']['this_hostname']['ip']
    local_ia = config['hosts']['this_hostname']['ia']
    local_port = config['local_port_start_range'] + dbusnum
    port = config['listener_port']

    cmd = ft_send
    cmd += " --quic-sender-only --local-ip %s --ip %s " % (local_ip, recv_ip)
    cmd += " --loacal-port %s --port %s --quic-dbus-index %s" % (local_port, port, dbusnum)

    outfile = config['result_dir'] + "hostlogs/" + config['this_label'] + "_" + dbusnum + "_" \
              + additional_suffix + config['flow_suffix']

    execute(cmd, outfile, False, None, True)
    proc = subprocess.Popen(cmd.split(), preexec_fn=os.setsid)
    return proc



# Start Athena
# TODO: num of flows not clear yet.
def start_athena(num_flows = 2):
    print("Starting Athena...")
    if skip_this_command(['sender', 'tester']):
        return
    command = config['athena_python_command'] + config['athena_location'] + num_flows

    resfile = config['result_dir'] + "hostlogs/" + config['this_label'] + config['athena_suffix']
    print_to_console = config['print_to_console']
    execute(command, resfile, True, None, print_to_console)

    print("Quic Listener Started.")

# Directly invoked from CLI
def run_calibrators():
    print("Getting Paths:")
    admitted_roles = ['sender', 'tester']
    if skip_this_command(admitted_roles):
        time.sleep(config['calibrator_duration'])
        return

    if config['this_role'] == 'sender' or config['this_role'] == 'tester':
        receivers = load_all_hostnames(config, filter_roles=['receiver'])
        all_processes = []
        local_port = config['local_port_start_range']
        for recv in receivers:
            recv_processes = []
            pathfile ="paths_" + recv
            if not os.path.exists(pathfile):
                print("No paths file for ", recv)
                continue
            with open(pathfile, 'r') as f:
                paths = f.read().split('\n')
            for path in paths:
                proc = start_scion_flow(path, recv, local_port)
                recv_processes.append(proc)
                local_port += 1
            all_processes.append(recv_processes)

        print("All Calibrator flows running...")
        time.sleep(config['calibrator_duration'])
        print("Stopping Calibrator flows...")

        for recv_procs in all_processes:
            # TODO read out and store the achieve throughputs for each calibrator. store receiver wise (probably)
            for proc in recv_procs:
                proc.kill()
        print("Calibrator Flows Stopped.")

# Directly invoked from CLI
def build():
    print("Building with Bazel:")
    os.system("cd " + config['scion_location'] + " bazel build ...")

# Directly invoked from CLI
def exec_rtt():
    print("Invoking RTT Script:")
    rtt_run(config)

def exec_from_args():
    #global parser
    parser = argparse.ArgumentParser()
    FUNCTION_MAP = {"run_all": run_all,
                    'runft': run_all_ft,
                    "run": run_ft_experiment,
                    "rtt": exec_rtt,
                    'paths': get_paths,
                    'probe': run_calibrators,
                    "build": build,
                    "setup": setup_sender,
                    "kill": kill
                    }
    parser.add_argument('command', choices=FUNCTION_MAP.keys())
    parser.add_argument('-n', action="store", dest="expname", default='default_experiment')
    args = parser.parse_args()
    # global exp_time
    config['name'] = args.expname
    infer_config()
    initiateLog()
    func = FUNCTION_MAP[args.command]
    func()

# Can be called directly from python, but will then need config dict passed
def run_all(pass_config=None):
    if pass_config:
        global config
        config = pass_config
        infer_config()
        initiateLog()

    rtt_run(config)
    time.sleep(2)
    run_all_ft()

# Can be called directly from python, but will then need config dict passed
def run_all_ft(pass_config=None):
    if pass_config:
        global config
        config = pass_config
        infer_config()
        initiateLog()
    setup_sender()
    time.sleep(2)
    run_ft_experiment()
    time.sleep(2)
    kill()
    print("Experiment finished.")
    print("Resultfolder: ", config['result_dir'])
    return config['result_dir']

def main(explicit_config=None):
    config = setup_configuration(explicit_config)
    rtt_run(config)
    run_ft_experiment()


if __name__ == "__main__":
    global config
    config = setup_configuration()
    exec_from_args()


