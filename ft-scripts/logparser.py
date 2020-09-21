#!/usr/bin/env python3.6
#Debugging:
# sudo python3.5 logparser.py  results/25/2/200/100/cubic/TCP-1_STABLE-1/2020-05-01--15-54-30/

# sudo rm results/25/2/200/100/cubic/TCP-1_STABLE-1/2020-05-01--15-54-30/condensed/*

from datetime import datetime
import os
import sys
import re
import subprocess
import math
import json
import pandas as pd
import matplotlib.pyplot as plt
import yaml
import numpy as np
from plotting import *
import pprint

# Notes:
# Now the statistics are gathered when processing the raw data.
# So far, there is only cropping available after the raw data processing, which messes up the stats.
# TODO: Allow for cropping that is applied during raw data traversal.
# --> this will probably make the loadCondensedData obsolete, which I think is not problem,
#       since the processing times were never that long anyway that it would require an intermediate repr.

# Note:
# The statistics gathering is not separated into origin (which could be relevant for the host)
# there could be a benefit in restructuring that at some later point.

logfolder = 'hostlogs/'
datafolder = 'hostdata/'
condenseddatafolder = 'condensed/'

TIMEAGGREGATION = 1  # Resolution of timestamps,  '1' rounds to 10ths of seconds, '2' rounds to 100ths, etc.
SMOOTHING       = 1

RESULT_FILE_PREFIX = ''


MERGE_INTERVALS = [[1,10]]#, [2,10]]

ALL_FLOWS = ['10.0.0.%d' % i for i in range(1,10+1)]
PLOT_KEYS = ['10.0.0.1', 'x.1-10'] #, 'x.2-10']
PLOT_CWND_KEYS = ['10.0.0.1']

SUM        = 'SUM'
MAX        = 'MAX'
AVG        = 'AVG'
VAR        = 'VAR'


plt.rc('text', usetex=True)
plt.rc('font', family='serif')
plt.rcParams['text.latex.preamble'] = [\
    r'\usepackage{amsmath}',\
    r'\usepackage{amssymb}']


# INPUT:
# key is either 'udpno' or 'seqno'
# Note: seqno != -1 => udpno == -1 && udpno != -1 => seqno == -1
# Requirement: the data passed contains only entries with 'identificator'-value != -1
#   Therefore: can not be a mix between UDP and TCP
# Requirement: the data passed is outbound traffic from sender to destination.
#   Therefore: ACK loss and latency is not calculated.
# OUTPUT:
# Losses are registered at timestamp where lost packet was sent.
# Latency is registered at the sender timestamp.

def loss_calc(received, sent, key):
    if received.shape[0] == 0 or sent.shape[0] == 0:
        return received, sent
    data = sent.append(received)
    data.sort_values(by=[key, 'timestamp'], inplace=True)
   # print("Concatenated and sorted: ")
    #print(data)

    # Only for Seqno: Find duplicate keys in sender, mark not-last ones as losses
    if key == 'seqno':
        data.loc[(data.measuredon != 'Dest') & ((data[(data.measuredon != 'Dest')]).duplicated(subset=key, keep='last')), 'loss'] = 1

        # Technically, there should not be duplicates on the receiver side, but for some reason this happens. Is it when the resending is due to timeout?
        # We will keep track of it as well.
        data.loc[(data.measuredon == 'Dest') & (data[(data.measuredon == 'Dest')].duplicated(subset=key, keep='last')), 'double_receive'] = 1
        data.loc[(data.measuredon == 'Dest') & (data[(data.measuredon == 'Dest')].duplicated(subset=key, keep='last')), 'loss'] = 1 # Only for avoidng

    # Safety Check: No duplicate keys left among sender or receiver
    #if ~data.duplicated(subset='udpno', keep=False):
    dest_has_dupl = data[(data.loss == 0) & (data.measuredon == 'Dest')].duplicated(subset=key, keep=False).any()
    sender_has_dupl = data[(data.loss == 0) & (data.measuredon != 'Dest')].duplicated(subset=key, keep=False).any()
    if dest_has_dupl or sender_has_dupl:
        print("Problem: Duplicates of ", key, " in dest/sender: " +  str(dest_has_dupl) + "/" + str(sender_has_dupl))
        print(data[(data.loss == 0) & (data.measuredon == 'Dest')])
        print(data[data[(data.loss == 0) & (data.measuredon == 'Dest')].duplicated(subset=key, keep=False)])
        raise Exception

    # Now all remaining duplicates that are loss == 0 are the sent-received pair, therefore acked.
    # Therefore: find nonacked pairs/nonduplicates and mark them as losses.
    # TODO: nuance, safety check: check for nonduplicates on receiver side.
    data.loc[((data.loss == 0) & ~(data[(data.loss == 0)].duplicated(subset=key, keep=False))), 'loss'] = 1

    # Safety check: All non-lost packets are acked, therefore shapex should be the same
    receiver_shape = data[(data.loss == 0) & (data.measuredon == 'Dest')].shape
    sender_shape = data[(data.loss == 0) & (data.measuredon != 'Dest')].shape
    print("Shapes: ", receiver_shape, " and ", sender_shape)
    if receiver_shape[0] != sender_shape[0]:
        print("Non-lost samples on receiver and sender do not match! Sender: ", sender_shape[0], " receiver: ", receiver_shape[0])
        with pd.option_context('display.max_rows', None):  # more options can be specified also
            #print(data)
            raise Exception
    eq = data[(data.loss == 0) & (data.measuredon == 'Dest')][key].values == data[(data.loss == 0) & (data.measuredon != 'Dest')][key].values
    if not eq.all():
        print("Equal length but not equal! ", eq)
        raise Exception

    # Logic
    data.loc[(data.loss == 0) & (data.measuredon != 'Dest'), 'num'] = 1
    data.loc[(data.loss == 0) & (data.measuredon != 'Dest'), 'latency_sum'] = \
        data.loc[(data.loss == 0) & (data.measuredon == 'Dest'), 'timestamp'].values - \
        data.loc[(data.loss == 0) & (data.measuredon != 'Dest'), 'timestamp'].values

    if key == 'seqno':
        data.loc[(data.measuredon == 'Dest') & (data[(data.measuredon == 'Dest')].duplicated(subset=key, keep='last')), 'loss'] = 0 # Only for avoidng
    return data[(data.measuredon == 'Dest')], data[(data.measuredon != 'Dest')]



# TCP Loss is registered at timestamp where lost packet was sent.
# For TCP loss, traverse timestamp  from below, keeping track of used seqno. when not fresh seqno, count loss.
# Note: since we only observe sender -> dest, any lost acks are not registered
def loss_calcFalse(received, sent):
    print(sent.shape)
    print(received.shape)
    sent.sort_values(by=['seqno', 'udpno', 'timestamp'], inplace=True)
    received.sort_values(by=['seqno', 'udpno', 'timestamp'], inplace=True)

    # Procedure for seqno
    sent.loc[sent.duplicated(subset='seqno', keep='last'), 'loss'] = 1
    if received[(received.seqno != 0)].shape[0] == sent[(sent.loss != 1) & (sent.seqno != 0)].shape[0]:
        if not (received[(received.seqno != 0)].seqno.values == sent[(sent.loss != 1) & (sent.seqno != 0)].seqno.values).all():
            print("SEQNO Filtered: Shapes fit, but seqno not identical.")
        else:
            # Calculate latency and add 'num'. Later, all will be summed up, and latency_sum / num will give avg lat.
            sent.loc[(sent.loss != 1) & (sent.seqno != 0), 'num'] = 1
            sent.loc[(sent.loss != 1) & (sent.seqno != 0), 'latency_sum'] = \
                received.loc[(received.seqno != 0), 'timestamp'].values - \
                sent.loc[(sent.loss != 1) & (sent.seqno != 0), 'timestamp'].values
    else:
        print("SEQNO Filtered: Shapes don't fit")
        print(sent[(sent.loss != 1) & (sent.seqno != 0)].shape)
        print(received[(received.seqno != 0)].shape)
        print(sent[(sent.loss != 1) & (sent.seqno != 0)])
        print(received[(received.seqno != 0)].seqno.values == sent[(sent.loss != 1) & (sent.seqno != 0)].seqno.values)

        print(received[(received.seqno != 0)])
    # Same procedure for udpno (copied)
    sent.loc[sent.duplicated(subset='udpno', keep='last'), 'loss'] = 1
    if received[(received.udpno != 0)].shape[0] == sent[(sent.loss != 1) & (sent.udpno != 0)].shape[0]:
        if not (received[(received.udpno != 0)].udpno.values == sent[(sent.loss != 1) & (sent.udpno != 0)].udpno.values).all():
            print("UDPNO Filtered: Shapes fit, but seqno not identical.")
        else:
            # Calculate latency and add 'num'. Later, all will be summed up, and latency_sum / num will give avg lat.
            sent.loc[(sent.loss != 1) & (sent.udpno != 0), 'num'] = 1
            sent.loc[(sent.loss != 1) & (sent.udpno != 0), 'latency_sum'] = \
                received.loc[(received.udpno != 0), 'timestamp'].values - \
                sent.loc[(sent.loss != 1) & (sent.udpno != 0), 'timestamp'].values
    else:
        print("UDPNO Filtered: Shapes don't fit")
        print(sent[(sent.loss != 1) & (sent.udpno != 0)].shape)
        print(received[(received.udpno != 0)].shape)
        print(received[(received.udpno != 0)].udpno.values == sent[(sent.loss != 1) & (sent.udpno != 0)].udpno.values)
        print(sent[(sent.loss != 1) & (sent.udpno != 0)])
        print(received[(received.udpno != 0)])

# Columns: timestamp, measuredon, src, dest, load, payload, udpno, seqno, ackno
def processTCPDdata(filename, econfig, timestep=0.1):
    df = pd.read_csv(filename, dtype={'timestamp': np.float64, 'measuredon': 'string', 'src': np.int64,
                                      'dest': np.int64, 'load': np.int64, 'payload': np.int64,
                                      'udpno': np.int64, 'seqno': np.int64, 'ackno': np.int64, 'id': np.int64})
    num_senders = econfig['inferred']['num_senders']
    receiver_no = num_senders + 1 # Todo: it's weird that sometimes 'Dest' is used and sometimes IP '11'. standardize!

    resampled = []
    for s in range(num_senders):

        sender = s + 1
        received_from_sender = df[(df.src == sender) & (df.dest == receiver_no) & (df.measuredon == 'Dest')]
        received_from_sender.loc[:, 'loss'] = 0  # Does not contribute to lossstat, but is used in loss_calc

        sent_by_sender = df[(df.measuredon == str(sender)) & (df.src == sender) & (df.dest == receiver_no)]
        sent_by_sender.loc[:, 'loss'] = 0
        sent_by_sender.loc[:, 'num'] = 0
        sent_by_sender.loc[:, 'latency_sum'] = 0.0
        received_from_sender.loc[:, 'double_receive'] = 0
        print("Shape:", received_from_sender.shape, " ", sent_by_sender.shape)
        try:
            received_from_sender[(received_from_sender.seqno != -1)], sent_by_sender[(sent_by_sender.seqno != -1)] = \
                loss_calc(received_from_sender[(received_from_sender.seqno != -1)], sent_by_sender[(sent_by_sender.seqno != -1)], 'seqno')
            received_from_sender[(received_from_sender.udpno != -1)], sent_by_sender[(sent_by_sender.udpno != -1)] = \
                loss_calc(received_from_sender[(received_from_sender.udpno != -1)], sent_by_sender[(sent_by_sender.udpno != -1)], 'udpno')
        except:
            print("Error calculating loss and latency.")
            raise Exception


        # Senderside contributes: loss, latency_sum, latency_contributor_count
        sent_by_sender = sent_by_sender.filter(items=['timestamp', 'loss', 'latency_sum', 'num'])
        sent_by_sender.loc[:, 'timestamp'] = pd.to_datetime(sent_by_sender.loc[:, "timestamp"], unit='s') # Need datetimeformat for resampling
        sent_by_sender = sent_by_sender.set_index('timestamp').resample(str(1000 * timestep) + 'ms', label='right').sum()
        sent_by_sender = sent_by_sender.add_suffix('_' + str(sender))
        resampled.append(sent_by_sender)

        print("Loss + Lat worked fine.")

        # Senderside contributes: load, payload, number of double received packets.
        received_from_sender = received_from_sender.filter(items=['timestamp', 'load', 'payload', 'double_receive'])
        received_from_sender['timestamp'] = pd.to_datetime(received_from_sender["timestamp"], unit='s') # Need datetimeformat for resampling
        received_from_sender = received_from_sender.set_index('timestamp').resample(str(1000*timestep) + 'ms', label='right').sum()
        received_from_sender = received_from_sender.add_suffix('_' + str(sender))  # To make it distinguishable in table
        resampled.append(received_from_sender)

    load_table = pd.concat(resampled, axis=1, join='outer')
    load_table = load_table.reset_index()
    load_table['abs_ts'] = load_table['timestamp'].values.astype(np.int64) / 1e9
    load_table['timestamp'] = (load_table.timestamp - load_table.timestamp.loc[0])  # Convert absolute time to timediff
    load_table['timestamp'] = load_table.timestamp.dt.total_seconds() # Elapsed seconds since start of experiment
    #print(load_table)
    load_table.fillna(0)
    load_table = load_table.sort_values(by=['timestamp'])
    load_table = load_table.set_index('timestamp')
    print("Fin")
    return load_table

#--------------------------------------------------------------------------------
# Parse and merge all tcpdump files
# Store in csv file.
# Fields: timestamp, measured-on, from, to, load, payload, udp, seqno, ackno

# TCPDump command: tcpdump -tt -i *interface* -n -e -v
# TCPDump examples, note that each packet has two lines.
#   1.: tcp ack
#   1591169992.383735 00:00:00:00:00:03 > 00:00:00:00:00:01, ethertype IPv4 (0x0800), length 66:
#       (tos 0x0, ttl 64, id 38676, offset 0, flags [DF], proto TCP (6), length 52)
#   *Newlne*10.0.0.3.5002 > 10.0.0.1.45687: Flags [.], cksum 0x142a (incorrect -> 0x17f2), ack 5793, win 1322,
#       options [nop,nop,TS val 2348940903 ecr 463900240], length 0

#   2.: tcp load
#   1591169992.384107 00:00:00:00:00:01 > 00:00:00:00:00:03, ethertype IPv4 (0x0800), length 1514:
#       (tos 0x0, ttl 64, id 41707, offset 0, flags [DF], proto TCP (6), length 1500)
#     *Newlne* 10.0.0.1.45687 > 10.0.0.3.5002: Flags [.], cksum 0x19d2 (incorrect -> 0x18d7), seq 225889:227337, ack 0, win 83,
#     options [nop,nop,TS val 463900259 ecr 2348940903], length 1448

#   3.: tcp load on receiver
#   1591170909.231527 00:00:00:00:00:01 > 00:00:00:00:00:03, ethertype IPv4 (0x0800), length 1514:
#   (tos 0x0, ttl 64, id 43218, offset 0, flags [DF], proto TCP (6), length 1500)
#     10.0.0.1.53723 > 10.0.0.3.5002: Flags [.], cksum 0x19d2 (incorrect -> 0x1d9f), seq 31857:33305, ack 1, win 83,
#     options [nop,nop,TS val 464817101 ecr 2349857745], length 1448

#   4.: tcp ack on receiver
#   1591170909.229867 00:00:00:00:00:03 > 00:00:00:00:00:02, ethertype IPv4 (0x0800), length 66:
#   (tos 0x0, ttl 64, id 38616, offset 0, flags [DF], proto TCP (6), length 52)
#     10.0.0.3.5002 > 10.0.0.2.42931: Flags [.], cksum 0x142b (incorrect -> 0xf1be), ack 43441, win 83,
#     options [nop,nop,TS val 1393565944 ecr 2522814530], length 0

#   5.: udp load
#       1591171072.412952 00:00:00:00:00:02 > 00:00:00:00:00:03, ethertype IPv4 (0x0800), length 1512:
#       (tos 0x0, ttl 64, id 4493, offset 0, flags [DF], proto UDP (17), length 1498)
#     10.0.0.2.49426 > 10.0.0.3.5003: UDP, length 1470

#   6. udp load on receiver
#      1591171072.346113 00:00:00:00:00:02 > 00:00:00:00:00:03, ethertype IPv4 (0x0800), length 1512:
#      (tos 0x0, ttl 64, id 3905, offset 0, flags [DF], proto UDP (17), length 1498)
#     10.0.0.2.49426 > 10.0.0.3.5003: UDP, length 1470

# Update: Extended TCPDump to also dump the first 78 bytes of the packet as hex.
# TCP Example:
# 1591624876.928245 00:00:00:00:00:01 > 00:00:00:00:00:02, ethertype IPv4 (0x0800), length 1514:
#   (tos 0x0, ttl 64, id 23761, offset 0, flags [DF], proto TCP (6), length 1500)
#     10.0.0.1.48571 > 10.0.0.2.5002: Flags [.], seq 4180415067:4180416515, ack 2499899782, win 83,
#     options [nop,nop,TS val 1333958879 ecr 1160376676], length 1448
# 	0x0000:  4500 05dc 5cd1 4000 4006 c448 0a00 0001
# 	0x0010:  0a00 0002 bdbb 138a f92c 125b 9501 7186
# 	0x0020:  8010 0053 19d1 0000 0101 080a 4f82 98df
# 	0x0030:  4529 f164 3637 3839 3031 3233 3435 3637
# UDP Example (counter marked with ** ** ) :
# 1591625197.068204 00:00:00:00:00:01 > 00:00:00:00:00:02, ethertype IPv4 (0x0800), length 1512:
#   (tos 0x0, ttl 64, id 27029, offset 0, flags [DF], proto UDP (17), length 1498)
#     10.0.0.1.46012 > 10.0.0.2.5003: UDP, length 1470
# 	0x0000:  4500 05da 6995 4000 4011 b77b 0a00 0001
# 	0x0010:  0a00 0002 b3bc 138b 05c6 19da **0000 0005** <--- UDP Counter
# 	0x0020:  5ede 45ed 0001 0a58 0000 0000 0000 0000
# 	0x0030:  3031 3233 3435 3637 3839 3031 3233 3435

def parseTCPDumpMininet(datafiles, filedestination):
    # timestamp, measuredon, src, dest, load, payload, udpno, seqno, ackno

    data = []
    data.append(['timestamp', 'measuredon', 'src', 'dest', 'load', 'payload', 'udpno', 'seqno', 'ackno', 'id'])
    for dfname in datafiles:

        measured_on = re.match(r'h(.+)-.*', dfname).group(1)
        datafile = RESULT_FILE_PREFIX+datafolder+dfname
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

                timestampMatcher = re.match(r'(\d+\.\d+).+\>.+', linestring)
                packetsizeMatcher = re.match(r'.+,\slength\s(\S+):.+', linestring)

                if (timestampMatcher and packetsizeMatcher): # If packet with timestamp and length:
                    try:
                        timestamp = timestampMatcher[1]
                        load = packetsizeMatcher[1]
                        id = int(re.match(r'.+,\sid\s(\d+).+', linestring).group(1))
                        offset = re.match(r'.+offset\s(\d+),.+', linestring)
                        if offset is None or int(offset.group(1)) != 0:
                            print("WARNING: Offset is not 0! ", linestring) # If this happens, it's a sign of fragmentation,
                                                                            # We should rethink the use of ID.
                        linestring = df.readline() # Proceed to second line of packet
                        linecounter += 1

                        hostOriginMatch = re.match(r'.*10\.0\.\d\.(\d+)\.\S+\s\>', linestring)
                        hostDestinationMatch = re.match(r'.+\>\s10\.0\.\d\.(\d+)\.\S+', linestring)
                        source = hostOriginMatch[1]
                        destination = hostDestinationMatch[1]
                        payload = int(re.match(r'.+,\slength\s(\S+)', linestring).group(1))

                        # Timeaggregation defines the granularity of the timestamps.
                        # timestamp = float(('%.'+str(TIMEAGGREGATION)+'f') % float(timestamp)) # Timestamp resolution
                        udpMatch = re.match(r'.+UDP.+', linestring)
                        sequenceMatch = re.match(r'.+seq\s(\d+):\d+.+', linestring) # Only capture right part of seqno range
                        # Assumption: only need right seqno. correct since iperf has consistent packet sizes.
                        #seqenceMatch = re.match(r'.+seq\s(\d+):(\d+).+', linestring)
                        ackedNrMatch = re.match(r'.+ack\s(\d+),.+', linestring)
                        if sequenceMatch:
                            seqno = int(sequenceMatch[1])
                        else:
                            seqno = -1
                        if ackedNrMatch:
                            ackno = ackedNrMatch[1]
                        else:
                            ackno = 0

                        # Parsing hexdump, depending if UDP or not
                        if udpMatch:
                            linestring = df.readline()
                            linestring = df.readline()  # Proceed to fourth line of packet
                            linecounter += 2
                            udpcMatch = re.match(r'\s*0x0010:\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\S+)\s+(\S+)', linestring)
                            udpno = int(udpcMatch[1] + udpcMatch[2], 16)
                        else:
                            udpno = -1
                        if sequenceMatch and udpMatch:
                            print("Sequence AND UDP. Weird!")

                        line = [timestamp, measured_on, source, destination, load, payload, udpno, seqno, ackno, id]
                        data.append(line)
                    except:
                        if re.match(r'.+ICMP.+', linestring) is not None:  # ICMP is ok.
                            continue
                        else: # Else: Print
                            print("FAIL when parsing: ", linestring)
            print("Read all %d lines.                     " % (filelength))

        # Write compressed data to a csv file
        np.savetxt(filedestination, np.array(data), delimiter=",", fmt='%s')



#--------------------------------------------------------------------------------
# Parse raw load data files
def parseCwndFiles(datafiles):
    print("Parsing CWND. Files: ", len(datafiles))

    cwndData = {}
    ssthreshData = {}

    for df in datafiles:
        print("File: ", df)
        m = re.match(r'h(\d+).*', df)
        if not m:
            continue
        hostNr = m.group(1)
        ip = '10.0.0.'+hostNr

        datafile = RESULT_FILE_PREFIX+logfolder+df
        print("Parsing datafile "+datafile+"...")

        cwndData[ip]     = {}
        ssthreshData[ip] = {}

        with open(datafile, 'r') as df:

            linestring = '_'
            while(linestring):
                linestring = df.readline()

                dataField = re.match(r'(\S+):.*cwnd:(\d+)', linestring)

                if dataField:
                    timestamp = float(dataField.group(1))
                    length = int(dataField.group(2))
                    cwndData[ip][timestamp] = length
                    continue

                dataField = re.match(r'(\S+):.*unacked:(\d+)', linestring)

                if dataField:
                    timestamp = float(dataField.group(1))
                    length = int(dataField.group(2))
                    ssthreshData[ip][timestamp] = length

    #print(cwndDatai + " und "+ ssthreshData)
    return cwndData, ssthreshData

# Assuming file structure (csv): unix-timestamp,packets-in-queue
def readQueueFile(datafile):
    print("Parsing queuefile.")
    df = pd.read_csv(datafile, header=None)
    ts_column = df.values[:,0]
    queue_column = df.values[:,1]
    return ts_column, queue_column

#--------------------------------------------------------------------------------
# Collect timestamps from load data
def collectTimestamps(data):

    timestamps = {}
    for path in data.keys():
        for origin in data[path].keys():
            for timestamp in data[path][origin].keys():
                timestamps[timestamp] = {}

    return list(timestamps.keys())


#--------------------------------------------------------------------------------
# Separate data into load and receive data
def separateData(data):
    recvData = {}
    sendData = {}
    dfileKeys = list(data.keys())
    for dfile in dfileKeys:
        if 'Dest' not in dfile: # It's one of the sending hosts
            hostNr = re.match(r'.*h(\d+)-.*', dfile).group(1)
            sendData = {**sendData, **data[dfile]} # Dumping all dictionaries into one
        else: # It's the destination host
            recvData = data[dfile]

    return recvData, sendData

#--------------------------------------------------------------------------------
# Calculate load statistics
def calculateLoadStat(data, timestamps, direction):
    allFlowsKey = 'x.1-10'
    loadStat = {}
    for origin in data.keys():
        print("Calc Load Stat: ", origin)
        flowLoadData          = [data[origin][ts] for ts in timestamps]
        loadStat[origin]      = {}
        loadStat[origin][SUM] = sum(flowLoadData)
        loadStat[origin][MAX] = max(flowLoadData)
        loadStat[origin][AVG] = loadStat[origin][SUM]/len(flowLoadData)
        loadStat[origin][VAR] = math.sqrt(1/len(flowLoadData) *\
                                sum([(fld-loadStat[origin][AVG])**2 for fld in flowLoadData]))

    with open(RESULT_FILE_PREFIX+direction+'Stat.json', 'w+') as loadStatFile:
        json.dump(loadStat, loadStatFile, sort_keys=True, indent=4)

    return loadStat


#--------------------------------------------------------------------------------
# Complete load data (no packets at a time result in a missing timestamp for an interface)
def fillinData(data, timestamps):

    for timestamp in timestamps:
        for origin in data.keys():
            try:
                data[origin][timestamp] += 0.0
            except KeyError:
                data[origin][timestamp] = 0.0

    return data


#--------------------------------------------------------------------------------
# Smooth load data (average)
def smoothData(data):

    smoothedData = {}
    for origin in data.keys():
        smoothedData[origin] = {}
        timestamps = list(data[origin].keys())
        for t in range(len(timestamps)):
            leftTimestamp  = max(t - SMOOTHING, 0)
            rightTimestamp = min(t + SMOOTHING, len(timestamps))
            relevantData = [data[origin][tt] for tt in timestamps[leftTimestamp:rightTimestamp]]
            smoothedData[origin][timestamps[t]] = sum(relevantData)/len(relevantData)

    return smoothedData


#--------------------------------------------------------------------------------
# Merge flow data (average)
def mergeFlows(data):
    mergeKeys  = ['x.%d-%d' % (MERGE_INTERVALS[i][0], MERGE_INTERVALS[i][1]) for i in range(len(MERGE_INTERVALS))]
    originalKeys = list(data.keys())
    for i in range(len(MERGE_INTERVALS)):
        mergeInterval = MERGE_INTERVALS[i]
        mergeKey = mergeKeys[i]
        data[mergeKey] = {}
        for origin in originalKeys:
            m = re.match(r'.+\.(\d+)$', origin)
            if not m:
                continue
            hostID = int(m.group(1))
            if hostID < mergeInterval[0] or hostID > mergeInterval[1]:
                continue
            for timestamp in data[origin].keys():
                relevantData = data[mergeKey]
                try:
                    relevantData[timestamp] += data[origin][timestamp]
                except KeyError:
                    relevantData[timestamp] = data[origin][timestamp]
    return data


def calculateTotal(df, num_senders):
    df['total_load'] = (df[['load_' + str(i+1) for i in range(num_senders)]]).sum(axis=1)
    df['total_payload'] = (df[['payload_' + str(i+1) for i in range(num_senders)]]).sum(axis=1)
    return df
    #TODO df['total_latency']


#--------------------------------------------------------------------------------
# Get load data
def calculateLoad(econfig):
    truncate_front = econfig['truncate_front']
    truncate_back = econfig['truncate_back']

    datafiles = [f for f in os.listdir(RESULT_FILE_PREFIX+datafolder)]
    condensed = RESULT_FILE_PREFIX + condenseddatafolder + 'tcpdump.csv'
    if not os.path.exists(condensed):
        parseTCPDumpMininet(datafiles, condensed)
    datatable = processTCPDdata(condensed, econfig, econfig['plot_load_resolution'])
    datatable = calculateTotal(datatable, econfig['inferred']['num_senders'])
    # Convert timestamps from datetime to elapsed time
    #print(datatable)

    exp_duration = econfig['send_duration']
    # TODO: better to have actual last tcpdump measurement instead of exp_duration as last timestamp
    datatable = datatable.truncate(before=truncate_front, after=exp_duration - truncate_back)
    #print(datatable)

    return datatable


# Adapted this technique from previous code. Not in use since the yaml config file system
def config_from_resfolderpath(resfolderpath):
    regex = r'results\/\d+\/(.+)\/(.+)\/(.+)\/(.+)\/(.+)\/.+'
    m = re.match(regex, resfolderpath)
    config = {}
    config['nSrcHosts'] = m.group(1)
    config['linkCap'] = m.group(2)
    config['bufferCap'] = m.group(3)
    config['ccFlavour'] = m.group(4)
    sendBehav = m.group(5)
    config['sendBehav'] = sendBehav.replace('_', ' ')
    return config

def loadExperimentConfig(resultpath):
    f = open(resultpath + 'config.yaml')
    config = yaml.load(f)
    f.close()
    return config


# Designed for load in MBytes, throughput in Mbits/sec and windows in K
def extract_iperf_tcp_client(filename):
    regex = r'\[\s+(\S+)\].+-(\S+)\s+sec\s+(\S+)\s+MBytes\s+(\S+)\s+MBytes/sec\s+(\d+)/(\d+)\s+(\d+)\s+(\d+)K/(\d+)\s+us.*'
    column_names = ['id', 'interval_end_time','transfer','bandwidth','write','err','retries','cwnd','rtt']
    return extract_data_regex(filename, column_names, regex)

def extract_iperf_udp_client(filename):
    column_names = ['id', 'interval_end_time','transfer','bandwidth','pps']
    regex = r'\[\s+(\S+)\].+-(\S+)\s+sec\s+(\S+)\s+MBytes\s+(\S+)\sMBytes/sec\s+(\d+)\spps.*'
    return extract_data_regex(filename, column_names, regex)

def extract_iperf_udp_server(filename):
    column_names = ['id', 'interval_end_time','transfer','bandwidth','jitter', 'lost', 'total', 'lossrate',
             'avg_lat', 'min_lat', 'max_lat', 'stdev_lat', 'pps']
    regex = r'\[\s+(\S+)\].+-(\S+)\s+sec\s+(\S+)\s+MBytes\s+(\S+)\s+MBytes/sec\s+(\S+)\sms\s+(\d+)/\s*(\d+)\s*\((\S+)%\)\s*(\S+)/\s*(\S+)/\s*(\S+)/\s*(\S+)\s+ms\s+(\d+)\spps.*'
    return extract_data_regex(filename, column_names, regex)

def extract_iperf_tcp_server(filename):
    column_names = ['id', 'interval_end_time', 'transfer', 'bandwidth', 'reads', 'reads_dist']
    regex = r'\[\s+(\S)\].+-(\S+)\s+sec\s+(\S+)\s+MBytes\s+(\S+)\s+MBytes/sec\s+(\d+)\s+(\S+:\S+).*'
    return extract_data_regex(filename, column_names, regex)

# Extract data from file
# designed to work for every kind of regex dataextraction
# Stores data in pandas dataframe. stored as strings
def extract_data_regex(filename, column_names, regex):
    print("Extracting from : ", filename)

    data = []
    with open(filename, 'r') as f:
        linestring = '0'
        while (linestring):
            linestring = f.readline()
            mobj = re.match(regex, linestring)
            if mobj is None:
               # print("Is none:", linestring)
                continue
            if len(mobj.groups()) != len(column_names):
                print("Mismatched for columnnames: ", column_names, ".\nLine:", linestring)
                continue
            #print("a", end="")
            sample = [mobj.groups()[i] for i in range(len(column_names))]
            data.append(sample)
    array = np.array(data)
    if data == []:
        print("No data available from: ", filename)
    else:
        print("Datashape of ", filename, ": ", array.shape)
    #print(array)
    return pd.DataFrame(array, columns=column_names, dtype="string")

def extractIperf(econfig):
    clients_data = []
    server_data = []
    protocols = [[a['protocol'] for a in client.values()][0] for client in econfig['sending_behavior']]
    for i in range(econfig['inferred']['num_senders']):
        iperfoutputfile = (RESULT_FILE_PREFIX + econfig['iperf_outfile_client']).replace("$", str(i+1))
        if 'tcp' in protocols[i]:
            clients_data.append(extract_iperf_tcp_client(iperfoutputfile))
        elif 'udp' in protocols[i]:
            clients_data.append(extract_iperf_udp_client(iperfoutputfile))
        else:
            print("ERROR: No parser for this protocol: ", protocols[i], ", file: ", iperfoutputfile)
    serverfile = RESULT_FILE_PREFIX + econfig['iperf_outfile_server_udp']
    if os.path.exists(serverfile):
        server_data.append(extract_iperf_udp_server(serverfile))
    serverfile = RESULT_FILE_PREFIX + econfig['iperf_outfile_server_tcp']
    if os.path.exists(serverfile):
        server_data.append(extract_iperf_tcp_server(serverfile))

    return clients_data, server_data



def loadFromCSV(filename):
    f = open(filename, 'r')
    df = pd.read_csv(f, header=None)
    return df

def main(savePlot=False):

    econfig = loadExperimentConfig(RESULT_FILE_PREFIX)

    tcpd_data = calculateLoad(econfig)
    cwndData, ssthreshData = parseCwndFiles([f for f in os.listdir(RESULT_FILE_PREFIX+logfolder)])

    startTimestamp = tcpd_data.index.values[0]
    endTimestamp =\
        tcpd_data.index.values[-1]
    startAbsTs = tcpd_data['abs_ts'].values[0]
    endAbsTs = tcpd_data['abs_ts'].values[-1]


    if econfig['plot_queue']:
        queueTs, queueVal = readQueueFile(RESULT_FILE_PREFIX + "queue_length.csv")

    print("Start/End timestamp: ", startTimestamp, endTimestamp)

    #avg_throughput = tcpd_stats[RESULT_FILE_PREFIX+datafolder+'hDest-eth0.log']['avg_throughput'] *8/1e6
    plt.figure('overview')

    num_axes = sum([econfig['plot_loss'], econfig['plot_throughput'],
                    econfig['plot_cwnd'], econfig['plot_latency'], econfig['plot_queue'], econfig['plot_memory'],
                   2 * econfig['plot_iperf_losslat']])
    fig, axes = plt.subplots(nrows=num_axes, num='overview', ncols=1, sharex=True)#, figsize=(10,8))

    xticks = []
    stats = {}
    ax_indx = 0
    if econfig['plot_throughput']:
        stats.update(plotLoad(axes[ax_indx], tcpd_data, startTimestamp, endTimestamp, econfig))
        ax_indx += 1
    if econfig['plot_cwnd']:
        stats.update(plotCwnd(axes[ax_indx], cwndData, ssthreshData, startAbsTs, endAbsTs, xticks))
        ax_indx += 1
    if econfig['plot_queue']:
        real_buffer_size = econfig['inferred']['bw_delay_product'] + econfig['switch_buffer']
        stats.update(plotQueue(axes[ax_indx], queueTs, queueVal, startAbsTs, endAbsTs, econfig['inferred']['bw_delay_product'],
                               real_buffer_size , xticks, econfig))
        ax_indx += 1
    if econfig['plot_latency']:
        stats.update(plotLatency(axes[ax_indx], tcpd_data, startTimestamp, endTimestamp, econfig))
        ax_indx += 1
    if econfig['plot_loss']:
        stats.update(plotLoss(axes[ax_indx], tcpd_data, startTimestamp, endTimestamp, econfig))
        ax_indx += 1
    if econfig['plot_memory']:
        memdata = loadFromCSV(RESULT_FILE_PREFIX+ "sysmemusage.csv")

        stats.update(plotMemory(axes[ax_indx], memdata, startAbsTs, endAbsTs, econfig))
        ax_indx += 1

    if econfig['plot_iperf_losslat']:
        iperf_client_data, iperf_server_data = extractIperf(econfig)
        plotLatencyIperf(axes[ax_indx], iperf_client_data, iperf_server_data, econfig, xticks)
        ax_indx += 1
        plotLossIperf(axes[ax_indx],  iperf_client_data, iperf_server_data, econfig, xticks)

    for j in range(num_axes):
        i = 1
        while i * 30 <= econfig['send_duration']:
            #axes[j].axvline(x=i * 30)
            i += 1

    #plt.tight_layout()
    #plt.subplots_adjust(0.1,0.1,0.99,0.92)
    plt.figure('overview')

    if savePlot:
        plt.savefig(RESULT_FILE_PREFIX+'loadDyn.png', dpi=150)
    else:
        plt.show()
    print(stats)

    with open(RESULT_FILE_PREFIX + econfig['stats_file'], 'w+') as statsfile:
        json.dump(stats, statsfile, indent=4)


if len(sys.argv) > 1:
    plt.figure('overview')
    plt.clf()

    RESULT_FILE_PREFIX = sys.argv[1]
    if len(sys.argv) > 2:
        main(savePlot=bool(sys.argv[2]))
    else:
        main(savePlot=True)
else:
    print("Please provide a result folder.")
