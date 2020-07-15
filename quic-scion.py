#!/usr/bin/python3

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
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

#
def parseTsharkSCIONQuic(datafiles, filedestination):
    # timestamp, measuredon, src, dest, load, payload, udpno, seqno, ackno

    data = []
    data.append(['timestamp', 'measuredon', 'src', 'dest', 'load', 'payload', 'udpno', 'seqno', 'ackno', 'id'])
    for dfname in datafiles:

        measured_on = 0
        datafile = dfname
        print("Parsing datafile "+datafile+"...")

        wcOutput = str(subprocess.check_output(("wc -l "+datafile).split()))
        filelength = int(re.match(r'b\'(\d+).+', wcOutput).group(1))
        linecounter = 0

        with open(datafile, 'r') as df:
            linestring = '_'
            while(linestring):
                linestring = df.readline()
                linecounter += 1

                # Show progress
                if linecounter % 100000 == 0:
                    print("Read %d / %d lines." % (linecounter, filelength), end="\r")

                timestampMatcher = re.match(r'.+\s(\d+\.\d+)\s.+UDP/SCION.+', linestring)
                packetsizeMatcher = re.match(r'.+\s+Len=(\d+),.+', linestring)

                if (timestampMatcher and packetsizeMatcher): # If packet with timestamp and length:
                    try:
                        timestamp = timestampMatcher[1]
                        load = packetsizeMatcher[1]
                       # linestring = df.readline() # Proceed to second line of packet
                       # linecounter += 1

                        source = 1
                        destination = 1
                        payload = 0
                        id = 0
                        seqno = 0
                        ackno = 0
                        udpno = 0
                        line = [timestamp, measured_on, source, destination, load, payload, udpno, seqno, ackno, id]
                        data.append(line)
                    except:
                        print("FAIL when parsing: ", linestring)
                #print("Failed to parse: ",  str(bool(timestampMatcher)) + ", " +  str(bool(packetsizeMatcher)))
            print("Read all %d lines.                     " % (filelength))

        # Write compressed data to a csv file
        np.savetxt(filedestination, np.array(data), delimiter=",", fmt='%s')

def calculateLoadSCION(datafile='tshark_test.log', timestep=1.0):
    datafiles = [datafile]
    condensed = 'tsharkdata.csv'
    #if not os.path.exists(condensed):
    parseTsharkSCIONQuic(datafiles, condensed)
    data = processTsharkdata(condensed, timestep)
    # with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
    #     print(data)
    return data

# Columns: timestamp, measuredon, src, dest, load, payload, udpno, seqno, ackno
def processTsharkdata(filename, timestep=1):
    df = pd.read_csv(filename, dtype={'timestamp': np.float64, 'measuredon': np.int64, 'src': np.int64,
                                      'dest': np.int64, 'load': np.int64, 'payload': np.int64,
                                      'udpno': np.int64, 'seqno': np.int64, 'ackno': np.int64, 'id': np.int64})

    df = df.filter(items=['timestamp', 'load'])
    df.loc[:, 'bitload'] = df.loc[:, "load"] * 8

    df.loc[:, 'timestamp'] = pd.to_datetime(df.loc[:, "timestamp"], unit='s')

    sent = df.set_index('timestamp').resample(str(1000 * timestep) + 'ms', label='right').sum()
    return sent

def limit_flow(rate_string, init=False):
    if init:
       # command = ('sudo tcset lo --rate %s --tc-command > temp.sh' % (rate_string))

        command = ('sudo tcset lo --rate %s' % (rate_string))
    else:
        command = ('sudo tcset lo --rate %s --change' % (rate_string))

       # command = ('sudo tcset lo --rate %s --change --tc-command > temp.sh' % (rate_string))

    #command = ('sudo tcset lo --rate %s --overwrite --tc-command > temp.sh' % (rate_string))

    #command = ("tc qdisc add dev lo root tbf rate %s peakrate %s" % (rate_string, rate_string))
    os.system(command)

    # f = open('temp.sh', 'r')
    # lines = f.read().split("\n")
    # for l in lines:
    #     if 'burst' in l:
    #         command = re.sub(r'burst\s+\S+\s+cburst.+', 'burst 1.0KB cburst 1.0KB', l)
    #         #command = re.sub(r'ceil\s+\S+\s+burst\s+\S+\s+cburst.+', 'ceil 2.0Kbit burst 2KB cburst 2KB', l)
    #     else:
    #         command = l
    #     print(command)
    #     os.system(command)

    #os.system('sh temp.sh')

    # os.system('sudo /sbin/tc qdisc del dev lo root')
    # os.system('sudo /sbin/tc qdisc del dev lo igress')
    # os.system('sudo /bin/ip link set dev ifb6094 down')
    # os.system('sudo /bin/ip link delete ifb6094 type ifb')
    # os.system('sudo /sbin/tc qdisc add dev lo root handle 17ce: htb default 1')
    # os.system('sudo /sbin/tc class add dev lo parent 17ce: classid 17ce:1 htb rate 32000000.0kbit')
    # os.system('sudo /sbin/tc class add dev lo parent 17ce: classid 17ce:117 htb rate %s ceil %s burst 0.0KB cburst 1250.0KB' % (rate_string, rate_string))
    # os.system('sudo /sbin/tc qdisc add dev lo parent 17ce:117 handle 2672: netem')
    # os.system('sudo /sbin/tc filter add dev lo protocol ip parent 17ce: prio 5 u32 match ip dsp 0.0.0.0/0 match ip src')


    print(datetime.fromtimestamp(time.time()), " changed to ", rate_string)



def runExperiment(datafile):

    print("As of now: This experiment is super specific to my configurations, so it won't work out of the box.")

    os.system('sudo pkill runuser')
    f = open(datafile, 'w')
    scionfolder = '/home/james/thesis/scionfork/scion/'
    programbase = scionfolder + 'go/examples/pingpong/'
    servercommand = (programbase + 'pingpong -mode server '
                       '-local 1-ff00:0:110,[127.0.0.1]:40002 -sciond 127.0.0.11:30255').split()
    clientcommand = (programbase + 'pingpong -mode client -remote 1-ff00:0:110,[127.0.0.1]:40002 '
                     '-local 1-ff00:0:111,[127.0.0.1]:0 -count 10000 -sciond 127.0.0.19:30255 -interval 3s -file /home/james/TheSting.mp4').split()
    tsharkcommand = ('sudo runuser -l james -c').split() + ["tshark -t e -i lo -Y scion.udp.dstport==40002"]

    tcsetcommand14 = 'sudo tcset lo --rate 14mbps --overwrite'
    tcsetcommand28 = 'sudo tcset lo --rate 28mbps --overwrite'
    tcsetcommand7 = 'sudo tcset lo --rate 7mbps --overwrite'
    tcdelcommand = 'sudo tcdel lo --all'
    os.system('sudo tcdel lo --all')
    serv = subprocess.Popen(servercommand)
    shark = subprocess.Popen(tsharkcommand, stdout=f, stderr=f)
    limit_flow('14mbps', init=True)
    #time.sleep(2)
    client = subprocess.Popen(clientcommand)
    n = 100
    start = time.time()
    for i in range(n):
        limit_flow('28mbps')
        limit_flow('7mbps')
    end = time.time()
    client.kill()
    time.sleep(2)

    serv.kill()
    time.sleep(2)

    shark.kill()
    time.sleep(2)
    os.system('sudo pkill runuser')
    os.system(tcdelcommand)

    f.close()
    print("Finished processes.")

    print("Start: ", start, "end: ", end)
    dt = end - start
    print("Total time: ", dt)
    print("Average time per limit change: ", dt / (2 * n))

def plot_rate(filename, timestep=0.001):
    f = open(filename, 'r')
    data = pd.read_csv(f)
    #data = data.set_index('timestamp')
    plt.figure('scion')
    plt.plot(data.index, data['bitload'] / timestep, label='bitload')
    #plt.hlines([14000000, 7000000, 28000000], xmin=0, xmax)
    plt.savefig('plot')

# Args are an alternative way of passing arguments. currently: 3 arguments: behaviorsummary, buffersize, tso_on
def main():
    datafile = 'tshark_test.log'
    runExperiment(datafile)
    timestep = 0.01
    filename = 'compressed_data'
    data = calculateLoadSCION(datafile=datafile, timestep=timestep)
    data.to_csv(filename)
    plot_rate(filename, timestep)

    print("Experiment finished.")
    # print("Resultfolder: ", config['result_dir'])
    # return config['result_dir']

if __name__ == "__main__":
    main()

