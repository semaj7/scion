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

def initiateLog(hostID):
    hostlogfile = config['result_dir']+"hostlogs/%s.log" % hostID
    config['hostlog'] = hostlogfile
    with hostlogfile as logfile:
        logfile.write(("%.6f" % time.time())+": "+config['this_hostname']+": Started\n")

def log(logContent):
    hostlogfile = config['hostlog']

    with open(hostlogfile, "a+") as logfile:
        logfile.write(("%.6f" % time.time())+": "+config['this_hostname']+": "+logContent+"\n")


def startTshark(hostID):
    for i in range(1):
        with open(config['result_dir']+'hostdata/'+str(hostID)+'-eth'+str(i)+'.log', 'w+') as f:
            tcpDumpCommmand = ('tcpdump -tt -i '+str(hostID)+'-eth'+str(i)+' -n -e -v -S -x -s 96').split()
            subprocess.Popen(tcpDumpCommmand, stdout=f, stderr=f)
            log("Started tcpdump.")


def startFshaper(hostconfig, hostname):
    hostname = config['this_hostname']
    initiateLog(hostname)
    startTshark(hostname)
    random.seed(hostname)
    time.sleep(2)
    fshaperoutput = config['result_dir'] + "fshaper.log"
    config['fshaper_log'] = fshaperoutput
    command = ""
    fout = open(fshaperoutput, 'w')
    log("Executing Command: " +  command)
    iperf_Process = subprocess.Popen(command.split(" "), stdout=fout)
    iperf_Process.communicate()
    fout.close()

# Start iperf server with TCP on destination hosts
def startQuicScionServer(config):
    resfile = config['result_dir'] + config['iperf_outfile_server_tcp']
    samplingperiod = config['iperf_sampling_period_server']
    fout = open(resfile, "w")
    tcpIperfCommand = ('iperf -s -p 5002 -e -i %d -t %d -f %s' % (samplingperiod, config['send_duration'] + 5, config['iperf_outfile_format'])).split()
    print(tcpIperfCommand)
    log("Starting TCP Server.")
    log("Command: " + str(tcpIperfCommand))
    proc = subprocess.Popen(tcpIperfCommand, stdout=fout)
    return proc, fout

def sender(hostconfig):
    hostname = config['this_hostname']
    initiateLog(hostname)
    startTshark(hostname)
    random.seed(hostname)
    time.sleep(2)
    startFshaper(hostconfig, hostname)
    log("Fshaper Exited.")

def receiver(hostconfig):
    hostname = config['this_hostname']
    initiateLog(hostname)
    startTshark(hostname)
    startQuicScionServer(hostconfig, hostname)
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
    resultDir += datetime.strftime(datetime.now(), "%Y-%m-%d--%H-%M-%S")
    resultDir += + "-" + config['name'] + '/'
    os.system('mkdir -p ' + resultDir)
    for rT in ['hostlogs/', 'hostdata/', 'condensed/']:
        os.mkdir(resultDir+rT)
    config['result_dir'] = resultDir
    return resultDir

def runExperiment(config):

    run_ft_experiments(config)

    resultFilePrefix = config['result_dir']
    print("Initiating logparser: " + resultFilePrefix)
    subprocess.call(('./logparser.py '+resultFilePrefix+' SAVEPLOT').split())
    subprocess.call(('cp /var/log/kern.log '+resultFilePrefix+'/tcpInternals.log').split())
    subprocess.call(('chmod 644 '+resultFilePrefix+'/tcpInternals.log').split())

# If an explicit config is passed, will ignore any CLI arguments
def setup_configuration(explicit_config=None):
    global config
    if explicit_config is None:
        # Load Default Config
        with open("config-defaults.yaml", "r") as ymlfile:
            config = yaml.load(ymlfile)
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
        name = args[1]
        config['name'] = name
    if len(args) > 2:
        config['this_hostname'] = args[2]
    # Create Result Directory
    resultFilePrefix = generateResultDir("emptyfornow", config, name)  # save it as: 'result_dir' config

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

