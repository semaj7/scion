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

def limit_flow(rate_string):
    command = ('sudo tcset lo --rate %s --overwrite' % (rate_string))
    os.system(command)
    print(datetime.fromtimestamp(time.time()), " changed to ", rate_string)



def runExperiment(datafile):

    print("As of now: This experiment is super specific for my configurations, so it won't work out of the box.")

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
    limit_flow('14mbps')
    serv = subprocess.Popen(servercommand)
    shark = subprocess.Popen(tsharkcommand, stdout=f, stderr=f)
    time.sleep(2)
    client = subprocess.Popen(clientcommand)
    time.sleep(20)
    limit_flow('28mbps')
    time.sleep(20)
    limit_flow('7mbps')
    time.sleep(20)
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


def plot_rate(filename, timestep=0.1):
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
    timestep = 0.001
    filename = 'compressed_data'
    data = calculateLoadSCION(datafile=datafile, timestep=timestep)
    data.to_csv(filename)
    plot_rate(filename, timestep)

    print("Experiment finished.")
    # print("Resultfolder: ", config['result_dir'])
    # return config['result_dir']

if __name__ == "__main__":
    main()

