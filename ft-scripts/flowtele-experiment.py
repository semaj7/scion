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
from ftutils import load_config

def initiateLog(hostID):
    hostlogfile = config['result_dir']+"hostlogs/%s.log" % hostID
    print("Create log at ", hostlogfile)

    config['hostlog'] = hostlogfile
    with open(hostlogfile, 'w') as logfile:
        logfile.write(("%.6f" % time.time())+": "+config['this_hostname']+": Started\n")

def log(logContent):
    hostlogfile = config['hostlog']

    with open(hostlogfile, "a+") as logfile:
        logfile.write(("%.6f" % time.time())+": "+config['this_hostname']+": "+logContent+"\n")


def startTshark():
    for i in range(1):
        with open(config['result_dir']+'hostdata/'+config['this_hostname']+"_dump.log", 'w+') as f:
            tcpDumpCommmand = ('tshark -i '+ config['tshark_net_interface'] + " -Y 'scion.udp.dstport==40002'")
            tcpDumpCommmand = ('tshark -i '+ config['tshark_net_interface'])
            subprocess.Popen(tcpDumpCommmand.split(), stdout=f, stderr=f)
            log("Started tshark.")


def startFshaperHost(hostconfig):
    hostname = config['this_hostname']
    startTshark()
    random.seed(hostname)
    time.sleep(1)
    fshaperlog = config['result_dir'] + "/hostlogs/" + config['this_hostname'] + "_fshaper.log"
    command = "/usr/local/go/bin/go run " + config['quic_sender_location']
    log("Delaying for Listener to prepare...")
    time.sleep(config['sender_delay_time'])
    log("Executing Command: " +  command)

    fout = open(fshaperlog, 'w')
    fout.write("Quic Client Output: \n")
    if config['print_to_console']:
        proc = subprocess.Popen(command.split(), preexec_fn=os.setsid)
    else:
        proc = subprocess.Popen(command.split(), preexec_fn=os.setsid, stdout=fout, stderr=fout)

    time.sleep(config['send_duration'])
    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    fout.close()

# Start iperf server with TCP on destination hosts
def startQuicScionServer(hostconfig):
    resfile = config['result_dir'] + "/hostlogs/" + config['this_hostname'] + "_quic_receiver.log"
    quicListenerCommand = "/usr/local/go/bin/go run " + config['quic_listener_location']
   # quicListenerCommand = "memcached"

    print("Executing: ", quicListenerCommand)
    log("Starting Quic Listener...")
    log("Executing Command: " + quicListenerCommand)
    fout = open(resfile, 'w')
    fout.write("Quic Client Output: \n")

    if config['print_to_console']:
        proc = subprocess.Popen(quicListenerCommand.split(), preexec_fn=os.setsid)
    else:
        proc = subprocess.Popen(quicListenerCommand.split(), preexec_fn=os.setsid, stdout=fout, stderr=fout)

    time.sleep(config['receiver_duration'])
    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    fout.close()

    return proc, fout

def sender(hostconfig):
    hostname = config['this_hostname']
    if hostconfig['role'] != 'sender':
        print("Something went wrong. Host ", hostname, " is not defined as sender.")
    initiateLog(hostname)
    startTshark()
    time.sleep(2)
    random.seed(hostname)
    startFshaperHost(hostconfig)
    log("Fshaper Exited.")

def receiver(hostconfig):
    hostname = config['this_hostname']
    if hostconfig['role'] != 'receiver':
        print("Something went wrong. Host ", hostname, " is not defined as receiver.")
    initiateLog(hostname)
    startTshark()
    time.sleep(2)
    startQuicScionServer(hostconfig)
    log("Receiver Exited.")

def run_ft_experiments(config):

    resultFilePrefix = config['result_dir']
    hostname = config['this_hostname']
    hostconfig = config['hosts'][hostname]
    if hostconfig is None:
        print("Invalid host name.")
    if hostconfig['role'] == 'sender':
        sender(hostconfig)
    elif hostconfig['role'] == 'receiver':
        receiver(hostconfig)
    else:
        print("Role ", hostconfig['role'], " not defined.")
    # Start destination host
    print("Sending over: ", time.time())
    time.sleep(5)

def generateResultDir(behavior_summary, config, name):

    resultDir = 'results/'
    #resultDir += datetime.strftime(datetime.now(), "%Y-%m-%d--%H-%M-%S") + "-"
    resultDir += config['name'] + '/'
    os.system('mkdir -p ' + resultDir)
    for rT in ['hostlogs/', 'hostdata/', 'condensed/']:
        os.system('mkdir -p ' + resultDir+rT)
    return resultDir

def runExperiment(config):

    run_ft_experiments(config)
    print("Experiment done.")
    resultFilePrefix = config['result_dir']
    # print("Initiating logparser: " + resultFilePrefix)
    # subprocess.call(('./logparser.py '+resultFilePrefix+' SAVEPLOT').split())
    # subprocess.call(('cp /var/log/kern.log '+resultFilePrefix+'/tcpInternals.log').split())
    # subprocess.call(('chmod 644 '+resultFilePrefix+'/tcpInternals.log').split())

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

    args = sys.argv
    if len(args) > 1:
        config['this_hostname'] = args[1]
    if len(args) > 2:
        experimentname = args[2]
        config['name'] = experimentname

    # Create Result Directory
    resultFilePrefix = generateResultDir("emptyfornow", config, experimentname)  # save it as: 'result_dir' config
    config['result_dir'] = resultFilePrefix

    # Dump Config
    f = open(resultFilePrefix + 'config.yaml', 'w')
    yaml.dump(config, f)
    f.close()
    return config

# Args are an alternative way of passing arguments. currently: 3 arguments: behaviorsummary, buffersize, tso_on
def main(explicit_config=None):
    if explicit_config is not None:
        config = setup_configuration(explicit_config)
    else:
        config = setup_configuration()
    runExperiment(config)
    print("Experiment finished.")
    print("Resultfolder: ", config['result_dir'])
    return config['result_dir']

if __name__ == "__main__":
    main()

