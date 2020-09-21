#!/usr/bin/env python3.7

# Takes 3 arguments:
# hostID: provide an integer X, assuming the sending hostnames are 'hX'
# destHostID: provide the desthostID
# configloc: the location of the configfile (default file won't work. some by cc-experiment inferred values are needed)

import sys
import subprocess
import re
import time
import random
import yaml
from pyroute2 import IPRoute

INTERVALS = 15
PROBING_INTERVAL = 1

NPATHS = 1

def initiateLog(hostID):

    with open(config['result_dir']+"hostlogs/%s.log" % hostID, "w+") as logfile:
        logfile.write(("%.6f" % time.time())+": "+hostID+": Started\n")


def log(hostID, logContent):

    with open(config['result_dir']+"hostlogs/%s.log" % hostID, "a+") as logfile:
        logfile.write(("%.6f" % time.time())+": "+hostID+": "+logContent+"\n")


def startTcpDump(hostID):
    for i in range(1):
        with open(config['result_dir']+'hostdata/'+str(hostID)+'-eth'+str(i)+'.log', 'w+') as f:
            tcpDumpCommmand = ('tcpdump -tt -i '+str(hostID)+'-eth'+str(i)+' -n -e -v -S -x -s 96').split()
            subprocess.Popen(tcpDumpCommmand, stdout=f, stderr=f)
            log(hostID, "Started tcpdump.")

def setupInterface(hostID, IPNum):
    ip = IPRoute()
    index = ip.link_lookup(ifname=''+hostID+'-eth1')[0]
    ip.addr('add', index, address='10.0.1.'+IPNum, mask=24)
    ip.close()
    log(hostID, "Second interface set up.")

def setTSO(hostID, on_mode):
    mode = "on" if on_mode else "off"
    for ifID in range(NPATHS):
        turnoffTSOCommand = ("ethtool -K %s-eth%d tso %s" % (hostID, ifID, mode)).split()
        output = str(subprocess.check_output(turnoffTSOCommand))
    log(hostID, "TSO turned " + str(mode))

def announceYourself(hostID, IPNum):
    for ifID in range(NPATHS):
        log(hostID, "Announce %s-eth%d" % (hostID,ifID))
        pingCommand = ("ping -c 3 -I %s-eth%d 10.0.%d.%d" % (hostID, ifID, ifID, desthostID)).split()
        subprocess.call(pingCommand)

# This will always be executed; regardless of 'protocol' config.
def iperf_command_base(currPath, desthostID, IPNum, duration, sampling_period, format):
    return ("iperf -c 10.0.%s.%d -B 10.0.%s.%s -t %d -i %s -e -f %s " % (currPath, desthostID, currPath, IPNum, duration, sampling_period, format)).split()

def tcp_command(cc_flavour, mss):
    return ("-p 5002 -Z %s -M %d " % (cc_flavour, mss)).split()

#def useCSRCommand(currPath, hostID):
#    return ("iperf -c 10.0.%s.%d -p 5002 -B 10.0.%s.%s -t %d -w %sM " % (currPath, DESTHOSTID, currPath, hostID, IPERF_DURATION, CSR_RATE)).split()

def udp_stable_command(cbr_as_pps, cbr_rate):
    if cbr_as_pps:
        return ("-p 5003 -u --udp-counters-64bit -b %spps " % (cbr_rate)).split()
    else:
        return ("-p 5003 -u --udp-counters-64bit -b %sm " % (cbr_rate)).split()
def udp_oscillation_command(currPath, IPNum, desthostID):
    return ("./oscillating-flow.py %s %d %s" % (IPNum, desthostID, config['result_dir'])).split()


def run(behavior_index, desthostID, config):
    print(config['sending_behavior'][behavior_index].keys())
    hostID, behavior = [(i, j) for i, j in config['sending_behavior'][behavior_index].items()][0]
    IPNum = behavior_index + 1
    initiateLog(hostID)
    log(hostID, ">> " + str(desthostID))
    announceYourself(hostID, IPNum)
    startTcpDump(hostID)
    random.seed(hostID)
    behavior = config['sending_behavior'][behavior_index][hostID] # TODO: make it compatible with custom hostnames
    log(hostID, "Sending behavior: " + str(behavior) )
    command = iperf_command_base(0, desthostID, IPNum, config['send_duration'], config['iperf_sampling_period'], config['iperf_outfile_format'])
    protocol = behavior['protocol']
    if 'tcp' in protocol:
        #reduceMTUCommand = ("ifconfig h%s-eth%d mtu 100" % (hostID, 0)).split()
        #subprocess.call(reduceMTUCommand)
        setTSO(hostID, behavior['tso_on'])
        if protocol == 'tcp-cubic':
            command += tcp_command('cubic', config['mss'])
        elif protocol == 'tcp-reno':
            command += tcp_command('cubic', config['mss'])
        elif protocol == 'tcp-bbr':
            command += tcp_command('bbr', config['mss'])
    elif 'udp' in protocol:
        if protocol == "udp-stable":
            command += udp_stable_command(config['cbr_as_pss'], config['inferred']['cbr_rate'])
        elif protocol == "udp-oscillation":
            command = udp_oscillation_command(0, hostID, desthostID)
        else:
            print("Undefined UDP behavior.")
            return

    currPath = '0'

    iperfoutputfile = (config['result_dir'] + config['iperf_outfile_client']).replace("$", str(IPNum))
    fout = open(iperfoutputfile, 'w')

    time.sleep(2)
    log(hostID, "Executing Command: " +  str(command))
    iperf_Process = subprocess.Popen(command, stdout=fout)
    cwind_period = float(config['cwind_sampling_period'])
    if 'tcp' in protocol:
        for i in range(int(config['send_duration'] / cwind_period)):
            time.sleep(cwind_period)
            ssOutput = str(subprocess.check_output('ss -ti'.split()))
            #log(hostID, ssOutput)
            m = re.match(r'.*(cwnd:\d+).*', ssOutput)
            if m is None:
                print("No match for: ", ssOutput )
                continue
            log(hostID, m.group(1))
    else:
        time.sleep(config['send_duration'])
    iperf_Process.communicate()
    fout.close()
    log(hostID, "Host %s finished experiment" % hostID)

def parseargs():
    behavior_index = int(sys.argv[1])
    desthostID = int(sys.argv[2])
    configfile_location = sys.argv[3]
    return behavior_index, desthostID, configfile_location

if __name__ == "__main__":
    behavior_index, desthostID, configloc = parseargs()
    f = open(configloc, "r")
    config = yaml.load(f)
    f.close()
    run(behavior_index, desthostID, config)

