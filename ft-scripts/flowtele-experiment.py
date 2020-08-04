#!/usr/bin/python3

#!/usr/bin/python

# First argument for sending behavior
# 2nd (optional): for additional buffersize (additional to bandwidth delay product)

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

RUN_ALL_COMMAND="run_all"
RUN_FT_CLIENTS_COMMAND="run"
RUN_RTT_COMMAND="rtt"
SETUP_FT_COMMAND='setup'
KILL_COMMAND='kill'
RUN_ALL_FT_COMMAND='run_ft'

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


def initiateLog():
    hostlogfile = config['result_dir']+"hostlogs/%s.log" % config['this_label']
    config['hostlog'] = hostlogfile
    if os.path.exists(hostlogfile):
        print("WARNING: this eperiment has already been run.")
        answer = input("Continue? ('y' for yes)")
        if answer != "y" and answer != 'yes':
            print("Not answered with 'y'. Abort.")
            return
    print("Create log at ", hostlogfile)
    with open(hostlogfile, 'w') as logfile:
        logfile.write(("%.6f" % time.time())+": "+config['this_hostname']+": Started\n")

def log(logContent):
    hostlogfile = config['hostlog']
    with open(hostlogfile, "a+") as logfile:
        logfile.write(("%.6f" % time.time())+": "+config['this_hostname']+": "+logContent+"\n")


def startTshark():
    fileoutput =config['result_dir']+'hostdata/'+config['this_hostname']+ config['tshark_suffix']
    tcpDumpCommmand = ('tshark -i '+ config['tshark_net_interface'] + " -Y 'scion.udp.dstport==40002'")
    tcpDumpCommmand = ('tshark -i '+ config['tshark_net_interface'])
    tcpDumpCommmand += " > " + fileoutput
    subprocess.Popen(tcpDumpCommmand.split())
    log("Started tshark.")

def startFshaperHost():
    random.seed(config['this_hostname'])
    fshaperlog = config['result_dir'] + "/hostlogs/" + config['this_hostname'] + "_fshaper.log"
    command = "/usr/local/go/bin/go run " + config['quic_sender_location']
    log("Delaying for Listener to prepare...")
    time.sleep(config['sender_delay_time'])
    log("Executing Command: " +  command)

    # fout = open(fshaperlog, 'w')
    # fout.write("Quic Client Output: \n")

    goenv = os.environ.copy()
    goenv["GO111MODULE"] = "off"

    if not config['print_to_console']:
        command += " > " + fshaperlog
    proc = subprocess.Popen(command.split(), preexec_fn=os.setsid, shell=False, env=goenv)
    time.sleep(config['send_duration'])
    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    #os.system("sudo pkill quic")
    # fout.close()

# Start iperf server with TCP on destination hosts
def startQuicScionServer():
    resfile = config['result_dir'] + "/hostlogs/" + config['this_hostname'] + "_quic_receiver.log"
    quicListenerCommand = "/usr/local/go/bin/go run " + config['quic_listener_location']
    #quicListenerCommand = "/usr/local/go/bin/go"

    print("Executing: ", quicListenerCommand)
    log("Starting Quic Listener...")
    log("Executing Command: " + quicListenerCommand)
    # fout = open(resfile, 'w')
    # fout.write("Quic Client Output: \n")

    if not config['print_to_console']:
        quicListenerCommand += " > " + resfile

    goenv = os.environ.copy()
    goenv["GO111MODULE"] = "off"
    proc = subprocess.Popen(quicListenerCommand.split(), preexec_fn=os.setsid, env=goenv)

    # time.sleep(config['receiver_duration'])
    # os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    # fout.close()

    return


def kill():
    print("Killing all flowtele programs...")
    os.system("sudo pkill tshark")
    os.system("sudo pkill quic_listener")
    return

def run_ft_clients():

    if config['this_role'] == 'sender' or config['this_role'] == 'tester':
        startFshaperHost()
        log("Fshaper Exited.")
    elif  config['this_role'] == 'receiver':
        print("Receiver. Nothing to do.")
        time.sleep(config['send_duration'])
    else:
        print("WARNING: Role ",  config['this_role'], " not defined.")
        return
    # Start destination host
    print("Sending over: ", time.time())


def setup():
    print("Initiating FlowTele Setup")
    startTshark()
    time.sleep(2)
    if config['this_role'] == 'receiver' or config['this_role'] == 'tester':
        startQuicScionServer()
    else:
        print("Sender: No server started.")
    print("Setup Done.")

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


def exec_rtt():
    print("Invoking RTT Script:")
    rtt_run(config)

def exec_from_args():
    #global parser
    parser = argparse.ArgumentParser()
    FUNCTION_MAP = {RUN_ALL_COMMAND: run_all,
                    RUN_ALL_FT_COMMAND: run_all_ft,
                    RUN_FT_CLIENTS_COMMAND: run_ft_clients,
                    RUN_RTT_COMMAND: exec_rtt,
                    SETUP_FT_COMMAND: setup,
                    KILL_COMMAND: kill
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
    setup()
    time.sleep(2)
    run_ft_clients()
    time.sleep(2)
    kill()
    print("Experiment finished.")
    print("Resultfolder: ", config['result_dir'])
    return config['result_dir']

# Args are an alternative way of passing arguments. currently: 3 arguments: behaviorsummary, buffersize, tso_on
def main(explicit_config=None):

    config = setup_configuration(explicit_config)
    rtt_run(config)
    run_ft_clients()


if __name__ == "__main__":
    global config
    config = setup_configuration()
    exec_from_args()


