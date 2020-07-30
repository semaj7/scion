#!/usr/bin/python3.6

import re
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import math

logfolder = 'hostlogs/'
datafolder = 'hostdata/'
condenseddatafolder = 'condensed/'

RESULT_FILE_PREFIX = ''

COLORS = {
    'h1': {
        0: (0.0, 0.5, 1.0),
        1: (0.54, 0.81, 0.94)
    },
    'h2': {
        0: (0.8, 0.0, 0.0),
        1: (0.91, 0.45, 0.32)
    },
    'h3': {
        0: (0.0, 0.5, 0.0),
        1: (0.55, 0.71, 0.0)
    },
    'h4': {
        0: (0.5, 0.0, 0.1),
        1: (0.55, 0.71, 0.0)
    },
    'h5': {
        0: (0.2, 0.1, 0.6),
        1: (0.55, 0.71, 0.0)
    },
    'h6': {
        0: (0.5, 0.5, 1.0),
        1: (0.54, 0.81, 0.94)
    },
    'h7': {
        0: (0.5, 0.0, 0.0),
        1: (0.91, 0.45, 0.32)
    },
    'h8': {
        0: (0.5, 0.5, 0.0),
        1: (0.55, 0.71, 0.0)
    },
    'h9': {
        0: (1.0, 0.0, 0.1),
        1: (0.55, 0.71, 0.0)
    },
    'h10': {
        0: (0.7, 0.1, 0.6),
        1: (0.55, 0.71, 0.0)
    },
    'h11': {
        0: (0.7, 0.1, 0.6),
        1: (0.55, 0.71, 0.0)
    },
    'h2-10': {
        0: (0.7, 0.1, 0.6),
        1: (0.55, 0.71, 0.0)
    },
    'h1-10': {
        0: (1.0, 0.0, 0.1),
        1: (0.55, 0.71, 0.0)
    },
}

PLOT_CWND_KEYS = ['10.0.0.1']

# plt.rc('text', usetex=True)
# plt.rc('font', family='serif')
# plt.rcParams['text.latex.preamble'] = [\
#     r'\usepackage{amsmath}',\
#     r'\usepackage{amssymb}']

# TODO: refactor confusing names
def plotLoad(ax, tcpd_data, starttime, endtime, econfig):
    plt.figure('overview')

    num_senders = econfig['inferred']['num_senders']
    linkCap = econfig['link_capacity']
    emulated_bufferCap = econfig['switch_buffer']
    real_bufferCap = econfig['inferred']['bw_delay_product'] + emulated_bufferCap
    sendBehav = econfig['inferred']['behavior_summary']
    sendBehav = sendBehav.replace('_', ' ')

    effective_duration = endtime - starttime
    converter = float(8.0 / 1e6)  # From bytes to Mbits
    timestep = econfig['plot_load_resolution']

    #print(tcpd_data.total_load[starttime:endtime])

    average_total_throughput = converter * np.sum(tcpd_data.total_load[starttime:endtime]) / effective_duration
    capacity = float(linkCap)
    fair_share = capacity/ float(num_senders)

    ax.hlines([fair_share], starttime, endtime, linestyles='-.', label='Fair Share', colors='orange')
    ax.hlines([capacity], starttime, endtime, linestyles='-.', label='Link Bandwidth Capacity', colors='green')

    average_throughput_senders = []
    print(tcpd_data.columns)
    for hostid in list(range(1, num_senders+1)):
        label = "load_" + str(hostid)
        if label in tcpd_data.columns:
            average = np.sum(tcpd_data[label][starttime:endtime]) * converter / effective_duration
            average_throughput_senders.append(average)
            if hostid in econfig['plot_hosts']:
                ax.plot(tcpd_data.index.values, converter * tcpd_data[label].values / timestep , ":", label=("h%s Throughput" % (hostid)))

    ax.plot(tcpd_data.index.values, converter * tcpd_data['total_load'].values / timestep , ':', label="Total Throughput")
    ax.set_title(r'\textbf{NFlows:} ' + str(num_senders) + r', \textbf{LinkCap:} ' + str(linkCap) + r'Mbps, ' + sendBehav + ' Buffer: ' + str(emulated_bufferCap))
    ax.hlines([average_total_throughput], starttime, endtime, linestyles='-.', label='Average Throughput', colors='blue')
    ax.set_xlabel(r'Time (s)')
    ax.set_ylabel(r'Rate (Mbps)')
    plt.locator_params(axis=ax, nbins=20)
    # ax.set_xticks(xticks)
    ax.set_ylim(bottom=0.0)
    ax.legend(loc=1)

    # Also make distribution plot
    avg_flow = np.average(average_throughput_senders)
    plotDistribution(average_throughput_senders, econfig['result_dir'] + 'throughput_dist.png',
                     lines=[avg_flow, fair_share],
                     labels=['Average Throughput', 'Fair Share'], colors=['blue', 'green'])

    # Return stats that were calculated here
    throughput_variance = np.var(np.array(average_throughput_senders))
    return {'total_throughput': float(average_total_throughput), 'utilization': float(average_total_throughput / linkCap),
            'timedelta': float(endtime - starttime), 'throughput_variance': float(throughput_variance),
            'throughput_average': float(avg_flow)}


# Graphdestination is a folder that holds copies of resulting graphs. Use it to aggregate from multiple experiments.
# Expname is the name of the overarching experiment. All runs of the same experiment will be summed up in a folder.
# Workpath is an optional path to where the experiment folders will be stored.. Default: this folder
# workpath+Expname folder needs to exist already.

def distrib(tcpd_data, starttime, endtime, econfig):

    #plt.clf()
    num_senders = econfig['inferred']['num_senders']
    linkCap = econfig['link_capacity']
    emulated_bufferCap = econfig['switch_buffer']
    real_bufferCap = econfig['inferred']['bw_delay_product'] + emulated_bufferCap
    sendBehav = econfig['inferred']['behavior_summary']
    sendBehav = sendBehav.replace('_', ' ')

    effective_duration = endtime - starttime
    converter = float(8.0 / 1e6)  # From bytes to Mbits

    capacity = float(linkCap)
    fair_share = capacity / float(num_senders)
    points = []
    for hostid in list(range(1, num_senders+1)):
        label = "load_" + str(hostid)
        if label in tcpd_data.columns:
            average = np.sum(tcpd_data[label][starttime:endtime]) * converter / effective_duration
            points.append(average)

    plt.hlines([fair_share],0.5, num_senders+0.5, linestyles='-.', label='Fair Share', colors='orange')
    plt.hlines(np.average(points), 0.5, num_senders+0.5, linestyles='-.', label='Average Throughput',
                      colors='blue')
    plt.bar(range(1, num_senders+1), points)


    #plt.set_title(r'\textbf{NFlows:} ' + str(num_senders) + r', \textbf{LinkCap:} ' + str(
     #   linkCap) + r'Mbps, ' + sendBehav + ' Buffer: ' + str(emulated_bufferCap))
    RESULT_FILE_PREFIX = econfig['result_dir']
    plt.savefig(RESULT_FILE_PREFIX + 'throughput_dist.png', dpi=150)
    #plt.clf()


def plotDistribution(points, destination, lines=[], colors=[], labels=[]):
    plt.figure('dist')
    #plt.clf()

    num_hlines = len(lines)
    num_points = len(points)
    for i in range(num_hlines):
        plt.hlines(lines[i], 0.5, num_points+0.5, linestyles='-', label=labels[i], colors=colors[i])
    plt.bar(list(range(1, num_points+1)), points)

    plt.savefig(destination, dpi=150)
    plt.clf()
    plt.figure('overview')


#--------------------------------------------------------------------------------
# Plot congestion control data
def plotCwnd(ax, cwndData, ssthreshData, startTimestamp, endTimestamp, xticks):
    plt.figure('overview')

    if len(PLOT_CWND_KEYS) == 0:
        return

    plotCwndData = {}
    print("start: ", startTimestamp)
    print("cwndData: ", cwndData)
    for origin in PLOT_CWND_KEYS:
        ts = sorted(cwndData[origin].keys())
    
        hostID = re.match(r'.+\.(.+)$', origin).group(1)
        ts = [t for t in ts if float(t) >= startTimestamp and float(t) <= endTimestamp]
        displayTs = [float(t)-startTimestamp for t in ts]
        ax.plot(displayTs, [cwndData[origin][t] for t in ts], label=("h%s" % hostID), color=COLORS["h"+hostID][0], linewidth=0.5)

        # If ts == 0
        if displayTs == []:
            print("In plotCWnd: displayTs is empty. ts: ", ts)
            return

        plotCwndData[origin] = {}
        for i in range(len(ts)):
            plotCwndData[origin]['%.1f' % displayTs[i]] = cwndData[origin][ts[i]]

        ts = sorted(ssthreshData[origin].keys())
        if len(ts) != 0:
            ts = [t for t in ts if float(t) >= startTimestamp and float(t) <= endTimestamp]
            displayTs = [float(t)-startTimestamp for t in ts]
            ax.plot(displayTs, [ssthreshData[origin][t] for t in ts], ':', label=("h%s (ssthresh)" % hostID), color=COLORS["h"+hostID][0])

    with open(RESULT_FILE_PREFIX+'cwndData.json', 'w+') as pDF:
        json.dump(plotCwndData, pDF, sort_keys=True, indent=4)

    ax.set_xlabel(r'Time (s)')
    ax.set_ylabel(r'cwnd (Segments)')
    #ax.set_xticks(range(int(displayTs[-1]+1)))
    #ax.set_xticks(xticks)
    ax.set_ylim(bottom=0.0)
    ax.legend()


# Plot Queue data
# Collect and print
def plotQueue(ax, ts, values, startTimestamp, endTimestamp, bwd_product, real_buffer_size, xticks, econfig):
    plt.figure('overview')

    # Crop
    displayTs = [float(ts[i]) - startTimestamp + econfig['truncate_front'] for i in range(len(ts)) if float(ts[i]) >= startTimestamp and float(ts[i]) <= endTimestamp]
    displayValues = [int(values[i])  for i in range(len(ts)) if float(ts[i]) >= startTimestamp and float(ts[i]) <= endTimestamp]

    # Calculate average queue length
    avg_queue = np.average(displayValues)
    ax.plot(displayTs, displayValues, label=("switch1"), linewidth=0.5)

    # Horizontal lines
    ax.plot([displayTs[0], displayTs[-1]], [avg_queue] * 2, '-', label='Buffer Size', color='blue', linewidth=0.5)
    ax.plot([displayTs[0], displayTs[-1]], [real_buffer_size] * 2, '-.', label='Buffer Size', color='green')
    ax.plot([displayTs[0], displayTs[-1]], [bwd_product] * 2, '-.', label='Bandwidth Delay Product', color='orange')
    ax.set_xlabel(r'Time (s)')
    ax.set_ylabel(r'Queue Length (packets)')
    ax.set_ylim(bottom=0.0)
    ax.legend()

    # Return stats that were calculated here
    return {'avg_queue': float(avg_queue)}


def plotLoss(ax, tcpd_data, starttime, endtime, econfig):
    plt.figure('overview')

    num_senders = econfig['inferred']['num_senders']
    linkCap = econfig['link_capacity']
    emulated_bufferCap = econfig['switch_buffer']
    real_bufferCap = econfig['inferred']['bw_delay_product'] + emulated_bufferCap
    sendBehav = econfig['inferred']['behavior_summary']
    sendBehav = sendBehav.replace('_', ' ')
    total_loss = 0
    for hostid in econfig['plot_hosts']:
        label = "loss_" + str(hostid)
        if label in tcpd_data.columns:
            total_loss += np.sum(tcpd_data[label].values)
            ax.plot(tcpd_data.index.values, tcpd_data[label].values, ':', label=("h%s Loss" % (hostid)))

    ax.set_xlabel(r'Time (s)')
    ax.set_ylabel(r'Loss')
    plt.locator_params(axis=ax, nbins=20)
    ax.set_ylim(bottom=0.0)
    ax.legend(loc=1)

    # Return stats that were calculated here
    return {'total_loss': int(total_loss)}


def plotLatency(ax, tcpd_data, starttime, endtime, econfig):
    plt.figure('overview')

    num_senders = econfig['inferred']['num_senders']
    linkCap = econfig['link_capacity']
    emulated_bufferCap = econfig['switch_buffer']
    real_bufferCap = econfig['inferred']['bw_delay_product'] + emulated_bufferCap
    sendBehav = econfig['inferred']['behavior_summary']
    sendBehav = sendBehav.replace('_', ' ')

    latency_sum = 0
    packet_sum = 0
    for hostid in econfig['plot_hosts']:
        label_lat = "latency_sum_" + str(hostid)
        label_num = "num_" + str(hostid)
        if label_lat in tcpd_data.columns and label_num in tcpd_data.columns:
            latency_sum += np.sum(tcpd_data[label_lat].values)
            packet_sum += np.sum(tcpd_data[label_num].values)
            ax.plot(tcpd_data.index.values, tcpd_data[label_lat].values * (1000.0 / tcpd_data[label_num].values), ':',
                    label=("h%s Latency" % (hostid)))

    ax.set_xlabel(r'Time (s)')
    ax.set_ylabel(r'Latency (ms)')
    plt.locator_params(axis=ax, nbins=20)
    ax.set_ylim(bottom=0.0)
    ax.legend(loc=1)

    # Return stats that were calculated here
    return {'avg_latency': float(latency_sum * 1000.0 / packet_sum), 'total_packets': int(packet_sum)}




def plotMemory(ax, df, start, end, econfig):
    ts = df[0]
    y_values = df[1]
    base_usage = y_values[0]
    print("base usage: ", base_usage)
    y_values = [int(y_values[i])  for i in range(len(ts)) if float(ts[i]) >= start and float(ts[i]) <= end]
    ts = [float(ts[i]) - start + econfig['truncate_front'] for i in range(len(ts)) if float(ts[i]) >= start and float(ts[i]) <= end]
    y_values = y_values - base_usage
    ax.plot(ts, y_values, "-", label='System Memory Usage')
    average = np.average(y_values)
    return {'avg_memory': average}


# Unused. Maybe at later point, just for quality control.
#----------------------------------------------------
def plotLatencyIperf(ax, iperf_client_data, iperf_server_data, econfig, xticks):
    # Clients
    for i in range(len(iperf_client_data)):
        df = iperf_client_data[i]
        relevantsamples = int(econfig['send_duration'] / econfig['iperf_sampling_period'])

        if "retries" in df.columns:
            # TODO: RTT/2 as latency is suboptimal. Redo it with TCPdump.
            ax.plot(df['interval_end_time'].astype(np.float)[:relevantsamples],
                    df['rtt'].astype(np.float)[:relevantsamples] / 1000, '-.', label='RTT/2 Client (TCP)')
        else:
            # TODO: will need UDP seqno and analyse in TCPdump
            print("Client Latency for UDP not supported with iperf data.")

    for i in range(len(iperf_server_data)):
        df = iperf_server_data[i]
        relevantsamples = int(econfig['send_duration'] / econfig['iperf_sampling_period_server'])
        if "lossrate" in df.columns:
            latency = (df['avg_lat'].str.replace('-', '0')).astype(np.float)
            timestamps = df['interval_end_time'].astype(np.float)
            ax.plot(timestamps[:relevantsamples], latency[:relevantsamples], '-.', label='Average Latency (UDP)')
        else:
            print("Overall Latency for TCP not supported with iperf data.")

    ax.set_xlabel(r'Time (s)')
    ax.set_ylabel(r'Latency (ms)')
    # ax.set_xticks(range(int(float(df['interval_end_time'].iloc[-2])))[0::5])
    # ax.set_xticks(range(econfig['send_duration']))
    # ax.set_xticks(xticks)

    ax.set_ylim(bottom=0.0)
    ax.legend()
    return {}


# Plot Loss data from iperf data
# TODO: time not synched with other plots, only with iperf itself. will need modification of logging
def plotLossIperf(ax, iperf_client_data, iperf_server_data, econfig, xticks):
    for i in range(len(iperf_client_data)):
        relevantsamples =  int(econfig['send_duration'] / econfig['iperf_sampling_period'])

        df = iperf_client_data[i]
        if "retries" in df.columns:
            ax.plot(df['interval_end_time'].astype(np.float)[:relevantsamples], df['retries'].astype(np.float)[:relevantsamples], '-.', label='Retries Client (TCP)')
        else:
            print("Client Loss for UDP not supported yet.")

    for i in range(len(iperf_server_data)):
        relevantsamples =  int(econfig['send_duration'] / econfig['iperf_sampling_period_server'])
        df = iperf_server_data[i]
        if "lossrate" in df.columns:
            ax.plot(df['interval_end_time'].astype(np.float)[:relevantsamples], df['lost'].astype(np.float)[:relevantsamples], '-.', label='Total Packets Lost (UDP)')
        else:
            print("Overall Loss for TCP not supported yet.")

    ax.set_xlabel(r'Time (s)')
    ax.set_ylabel(r'Loss (packets)')
    #ax.set_xticks(range(econfig['send_duration']))
    ax.set_xticks(xticks)

    #ax.set_xticks(range(int(float(df['interval_end_time'].iloc[-2])))[0::5])
    ax.set_ylim(bottom=0.0)
    ax.legend()
    return {}

# Readin stats files form resfolders of multiple experiments
def plot_experiment_comparison(curvevarname, xname, ynames, data, destfile):
    plt.figure("comparison")

    axes = []
    fig, axes = plt.subplots(nrows=len(ynames), num='comparison', ncols=1)
    fig.set_figheight(4 * len(ynames))
    fig.set_figwidth(6)
    for i in range(len(ynames)):
        axes[i].set_title(ynames[i])
    # Group data based on the different values in curvename
    grouped = data.groupby(curvevarname)
    for key in grouped.groups.keys():
        #print(key)
        grp = grouped.get_group(key)
        #print(grouped.get_group(key))
        for i in range(len(ynames)):
            #print(grp[ynames[i]])
            repetitions_group = grp[ynames[i]].groupby(xname)
            index = repetitions_group.groups.keys()
            mean = repetitions_group.mean()
            stdd = repetitions_group.std()
            axes[i].errorbar(index, mean, stdd, fmt='-o', label=curvevarname + " " + str(key))
            #axes[i].plot(grp[xname], grp[ynames[i]],)
    #break
    #plt.legend()
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05),
              fancybox=True, ncol=5)
    #   plt.show()
    print('saving plot in: ', destfile)
    plt.savefig(destfile + 'comparison.png', dpi=150)
