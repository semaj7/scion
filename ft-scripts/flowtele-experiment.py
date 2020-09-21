#!/usr/bin/env python3.7


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

# kill_procs:         stop all programs

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
import psutil
from os.path import join
import threading
import multiprocessing
import asyncio

# Checks if the current host belongs to roles that should perform this command.
# Returns 'true' if should skip
# Also prints suitable messages
def skip_this_command(advancing_roles):
    this_role = config["this_role"]
    if this_role in advancing_roles:
        print("This machine has role ", this_role, ". Will perform this command.")
        return False
    else:
        print("This machine has role ", this_role, ". Will skip this command.")
        return True


# Necessary to be executed at some point.
def infer_config():
    hostname = os.uname()[1]
    config["this_hostname"] = hostname
    label = config["hostname_label_map"][hostname]
    config["this_label"] = label
    role = config["label_role_map"][label]
    config["this_role"] = role

    hostdata_dir = "hostdata"
    hostlogs_dir = "hostlogs"
    condensed_dir = "condensed"
    paths_dir = "paths"
    # Create Result Directory
    resultFilePrefix = generateResultDir(
        config["name"], (hostdata_dir, hostlogs_dir, condensed_dir, paths_dir)
    )  # save it as: 'result_dir' config
    config["result_dir"] = resultFilePrefix

    # Infer Filelocations
    config["neighbors_file"] = join(config["result_dir"], config["neighbors_file"])
    config["processes_file"] = join(config["result_dir"], config["processes_file"])
    config["data_dir"] = join(config["result_dir"], hostdata_dir)
    config["perf_record_file"] = join(config["data_dir"], config["perf_record_file"])
    config["perf_dump_file"] = join(config["data_dir"], config["perf_dump_file"])
    config["parsed_destination"] = join(
        config["result_dir"], condensed_dir, config["parsed_destination"]
    )
    config["log_dir"] = join(config["result_dir"], hostlogs_dir)
    config["iperf_log"] = join(config["log_dir"], config["iperf_log"])
    config["path_dir"] = join(config["result_dir"], "paths")

    # Dump Config
    with open(join(config["result_dir"], "config.yaml"), "w") as f:
        yaml.dump(config, f)


# If an explicit config is passed, will ignore any CLI arguments
def setup_configuration(explicit_config=None):
    global config
    if explicit_config is None:
        # Load Default Config
        config = load_config("ft-scripts/config-defaults.yaml")
        # Load Arguments
        # setLogLevel(config['scion_log_level'])
        # if len(sys.argv) > 1:
        #     parse_args(config)
        # else:
        #     print("No options provided. Will execute default experiment.")
    else:
        config = explicit_config
        print("Loaded an explicit config.")

    return config


def initiateLog():
    hostlogfile = join(config["log_dir"], "%s.log" % config["this_label"])
    config["hostlog"] = hostlogfile
    if os.path.exists(hostlogfile):
        print(
            "WARNING: this eperiment named '"
            + config["name"]
            + "' has already been run."
        )
        answer = input("Continue? ('y' for yes)")
        if answer != "y" and answer != "yes":
            print("Not answered with 'y'. Abort.")
            return
    print("Create log at ", hostlogfile)
    with open(hostlogfile, "w") as logfile:
        logfile.write(
            ("%.6f" % time.time()) + ": " + config["this_label"] + ": Started\n"
        )


def log(logContent):
    hostlogfile = config["hostlog"]
    with open(hostlogfile, "a+") as logfile:
        logfile.write(
            ("%.6f" % time.time())
            + ": "
            + config["this_label"]
            + ": "
            + logContent
            + "\n"
        )


# If print_to_console, then outfile is ignored. This is therefore only used for debugging.
def execute(
    command, outfile, setsid=False, env=None, print_to_console=False, sudo=False
):
    cmdStringArgs = [str(x) for x in command]
    if sudo:
        cmdStringArgs = ["sudo"] + cmdStringArgs
    print("Executing: ", cmdStringArgs)
    print("outfile: ", outfile)
    print("env: ", env)
    print(os.setsid if setsid else None)
    if not print_to_console:
        # TODO: having both '>' and 'stdout=' seems odd.
        # cmdStringArgs += " > " + outfile
        print(f"run by redirecting output to {outfile}")
        with open(outfile, "w") as outfile:
            proc = subprocess.Popen(
                cmdStringArgs,
                start_new_session=setsid,
                # preexec_fn=os.setsid if setsid else None,
                env=env,
                stderr=outfile,
                stdout=outfile,
            )
    else:
        print(f"run without redirecting")
        proc = subprocess.Popen(
            cmdStringArgs , start_new_session=setsid, env=env
        )
    return proc

# threading/multiprocessing stuff
# t = threading.Thread(target=fThread, args=(1,))
# print(multiprocessing.get_start_method())
# ctx = multiprocessing.get_context('spawn')
# print('main thread')
# PrintProcessInfo()
# t = ctx.Process(target=fThread, args=(cmdStringArgs, setsid, env,))
# t.start()
# proc = None
#proc = lambda: asyncioThread(cmdStringArgs)
# asyncio.run(asyncioThread(cmdStringArgs))

# # If print_to_console, then outfile is ignored. This is therefore only used for debugging.
# def create_async_io_process(
#     command, outfile, setsid=False, env=None, print_to_console=False, sudo=False
# ):
#     cmdStringArgs = [str(x) for x in command]
#     if sudo:
#         cmdStringArgs = ["sudo"] + cmdStringArgs
#     print(os.setsid if setsid else None)
#     proc = asyncioThread(cmdStringArgs)
#     # asyncio.run(asyncioThread(cmdStringArgs))
#     return proc

# async def asyncioThread(cmdStringArgs):
#     print("Executing: ", cmdStringArgs)
#     PrintProcessInfo()
#     proc = await asyncio.create_subprocess_exec(*cmdStringArgs)
#     return proc
    
# def fThread(cmdStringArgs, setsid, env):
#     proc = subprocess.Popen(cmdStringArgs, preexec_fn=os.setsid if setsid else None, env=env)
#     print(f'thread with pid {proc.pid} started')
#     PrintProcessInfo()

# def fThreadAsyncio(cmdStringArgs, setsid, env):
#     proc = subprocess.Popen(cmdStringArgs, preexec_fn=os.setsid if setsid else None, env=env)
#     print(f'thread with pid {proc.pid} started')
#     PrintProcessInfo()


def PrintProcessInfo():
     print(f"os.getegid() {os.getegid()}")
     print(f"os.geteuid() {os.geteuid()}")
     print(f"os.getgid() {os.getgid()}")
     print(f"os.getlogin() {os.getlogin()}")
     print(f"os.getpgid(0) {os.getpgid(0)}")
     print(f"os.getpgrp() {os.getpgrp()}")
     print(f"os.getpid() {os.getpid()}")
     print(f"os.getppid() {os.getppid()}")
     print(f"os.getpriority(os.PRIO_PROCESS, 0) {os.getpriority(os.PRIO_PROCESS, 0)}")
     print(f"os.getpriority(os.PRIO_PGRP, 0) {os.getpriority(os.PRIO_PGRP, 0)}")
     print(f"os.getpriority(os.PRIO_USER, 0) {os.getpriority(os.PRIO_USER, 0)}")
     print(f"os.getresuid() {os.getresuid()}")
     print(f"os.getresgid() {os.getresgid()}")
     print(f"os.getuid() {os.getuid()}")
#####################################################################################


def startTshark():
    fileoutput = join(
        config["data_dir"], config["this_label"] + config["tshark_suffix"]
    )
    ifs = config["hosts"][config["this_hostname"]]["tshark_net_interface"]
    # tcpDumpCommmand = ('tshark -i '+ config['tshark_net_interface'] + " -Y 'scion.udp.dstport==40002'")
    tcpDumpCommmand = ["tshark", "-i", ifs]
    execute(tcpDumpCommmand, fileoutput, False, None, False, True)
    print("Started tshark.")


def start_fshaper():
    random.seed(config["this_hostname"])  # Unsure if/why needed
    fshaperlog = join(
        config["log_dir"],
        "hostlogs",
        config["this_label"] + config["fshaper_suffix"],
    )
    command = [config["ftsocket_location"], "--fshaper-only"]
    print_to_console = config["print_to_console"]
    proc = execute(command, fshaperlog, True, None, print_to_console)


# Start iperf server with TCP on destination hosts
def start_listeners(num=2, scion=True):
    print("Starting Quic Listener...")
    print(config["hosts"])

    local_ip = config["hosts"][config["this_hostname"]]["ip"]
    local_ia = config["hosts"][config["this_hostname"]]["ia"]

    command = [config["quic_listener_location"]]
    if scion:
        command += ["--scion"]

    # TODO: unsure how to treat NUM
    command += ["--local-ia", local_ia, "--ip", local_ip, "--num", num]

    resfile = join(
        config["log_dir"],
        config["this_label"] + config["quicrecv_suffix"],
    )
    print_to_console = config["print_to_console"]
    execute(command, resfile, True, None, print_to_console)

    print("Quic Listener Started.")
    # time.sleep(config['receiver_duration'])
    # os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    # fout.close()

    return


# Directly invoked from CLI
def kill_procs():
    print("Killing all flowtele programs...")
    os.system("sudo pkill -f tshark")
    # the -f flag is necessary to use the full name (otherwise, if the path to the executable is
    # long, the executable name might not be included)
    os.system("sudo pkill -f flowtele\_listener")
    os.system("sudo pkill -f flowtele\_socket")
    os.system("sudo pkill -f athena")
    return


# Directly invoked from CLI
def list_procs():
    print("Listing all flowtele processes...")
    related_procs = []
    for proc in psutil.process_iter(attrs=["pid", "name"]):
        if proc.name() in ("tshark", "flowtele_listener", "flowtele_socket", "athena"):
            related_procs.append((proc.name(), proc.pid))
    print(related_procs)
    return


def run_quicnative_experiment():
    # Start Clients

    time.sleep(config["send_duration"])
    print("Sending for ", config["send_duration"] + " seconds..")
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
    for flownum in range(config["num_flows"]):
        proc = start_scion_flow(best_path, recv, flownum)
        procs.append(proc)

    time.sleep(config["send_duration"])
    print("Sending for ", config["send_duration"] + " seconds..")

    # Stop Clients
    for proc in procs:
        proc.kill()
    print("Sending finished.")


# Directly invoked from CLI
def run_ft_experiment():
    print("Running the Main Flowtele Experiment..")
    admitted_roles = ["sender", "tester"]
    if skip_this_command(admitted_roles):
        time.sleep(config["send_duration"])
        return

    if config["use_scion"]:
        run_scion_experiment()
    else:
        run_quicnative_experiment()

    print("Sending over: ", time.time())


# Directly invoked from CLI
def start_tshark_and_listeners():
    print("Starting the listeners")
    startTshark()
    if skip_this_command(["receiver", "tester"]):
        print("Delaying for Listener to prepare...")
        time.sleep(config["sender_delay_time"])
        return
    start_listeners(num=config['num_flows'])


# Directly invoked from CLI
def setup_sender():
    print("Setting up Sender")

    if skip_this_command(["sender", "tester"]):
        return
    if config["use_shaping"]:
        start_fshaper()
        start_athena()


def get_path(remote_name):
    print("Getting paths for ", remote_name)
    local_ia = config["hosts"][config["this_hostname"]]["ia"]
    ftsocket_exec = config["ftsocket_location"]
    remote_ia = config["hosts"][remote_name]["ia"]
    command = [
        ftsocket_exec,
        "--mode",
        "fetch",
        "--local-ia",
        local_ia,
        "--remote-ia",
        remote_ia,
    ]
    remote_label = config["hostname_label_map"][remote_name]
    outname = join(config["path_dir"], "paths_" + remote_label + ".txt")
    proc = execute(command, outname, False, None, False)
    # wait for command to write output file
    proc.wait()
    numpaths = int(
        "".join(
            filter(
                str.isdigit,
                str(
                    subprocess.run(
                        ("wc -l " + outname).split(), capture_output=True
                    ).stdout
                ).split(" ")[0],
            )
        )
    )

    print("Number of paths found: ", numpaths)


# Directly invoked from CLI
# Can be executed on every machine. Will act according to role.
def get_paths():
    print("Getting Paths:")
    admitted_roles = ["sender", "tester"]
    if skip_this_command(admitted_roles):
        return

    receivers = load_all_hostnames(config, filter_roles=["receiver"])
    for recv in receivers:
        get_path(recv)


# Start a quic flow through scion over the given path to the recv-name.
# Each flow needs a dbusnum that identifies it in the shaper.
def start_scion_flow(path, recv_hostname, dbusnum, additional_suffix=""):

    print("Starting Flow to host ", recv_hostname, " through path ", path)
    thishostname = config["this_hostname"]
    ft_send = config["ftsocket_location"]
    recv_ip = config["hosts"][recv_hostname]["ip"]
    recv_ia = config["hosts"][recv_hostname]["ia"]
    local_ip = config["hosts"][thishostname]["ip"]
    local_ia = config["hosts"][thishostname]["ia"]
    local_port = config["local_port_start_range"] + dbusnum
    port = config["listener_port"]
    max_data = config["max_data"]

    cmd = [ft_send]
    cmd += ["--quic-sender-only", "--scion", "--local-ip", local_ip, "--ip", recv_ip, "--local-ia", local_ia, "--remote-ia", recv_ia]
    cmd += ["--path", path, "--local-port", local_port, "--port", port, "--quic-dbus-index", dbusnum, "--num", config['num_flows']]
    cmd += ["--max-data", max_data]

    outfile = join(
        config["log_dir"],
        config["this_label"]
        + "_"
        + str(dbusnum)
        + "_"
        + additional_suffix
        + config["flow_suffix"],
    )

    proc = execute(cmd, outfile, True, None, True)
    return proc


# Start a quic flow through regular internet to reciever
# Each flow needs a dbusnum that identifies it in the shaper.
# TODO, unfinished, not thought through


def start_quic_flow(recv_hostname, dbusnum, additional_suffix=""):
    print("Starting Flow to host ", recv_hostname, " through path ", path)

    ft_send = config["ftsocket_location"]
    recv_ip = config["hosts"][recv_hostname]["ip"]
    recv_ia = config["hosts"][recv_hostname]["ia"]
    local_ip = config["hosts"]["this_hostname"]["ip"]
    local_ia = config["hosts"]["this_hostname"]["ia"]
    local_port = config["local_port_start_range"] + dbusnum
    port = config["listener_port"]

    cmd = [ft_send]
    cmd += ["--quic-sender-only", "--local-ip", local_ip, "--ip", recv_ip]
    cmd += ["--local-port", local_port, "--port", port, "--quic-dbus-index", dbusnum]

    outfile = join(
        config["log_dir"],
        config["this_label"]
        + "_"
        + dbusnum
        + "_"
        + additional_suffix
        + config["flow_suffix"],
    )

    execute(cmd, outfile, False, None, True)
    proc = subprocess.Popen(cmd.split(), preexec_fn=os.setsid)
    return proc

# Start Athena
# TODO: num of flows not clear yet.
def start_athena(num_flows=2):
    print("Starting Athena...")
    if skip_this_command(["sender", "tester"]):
        return
    command = [config["athena_python_command"], config["athena_location"], num_flows]

    resfile = join(config["log_dir"], config["this_label"] + config["athena_suffix"])
    print_to_console = config["print_to_console"]
    execute(command, resfile, True, None, print_to_console)

    print("Quic Listener Started.")


# Directly invoked from CLI
def run_calibrators():
    print("Getting Paths:")
    admitted_roles = ["sender", "tester"]
    if skip_this_command(admitted_roles):
        time.sleep(config["calibrator_duration"])
        return

    counter = 0
    if config["this_role"] in ("sender", "tester"):
        receivers = load_all_hostnames(config, filter_roles=["receiver"])
        all_processes = []
        local_port = config["local_port_start_range"]
        n_connections = 0
        for recv in receivers:
            recv_processes = []
            pathfile = join(
                config["path_dir"],
                "paths_" + config["hostname_label_map"][recv] + ".txt",
            )
            if not os.path.exists(pathfile):
                print("Paths file does not exist: ", pathfile)
                continue
            with open(pathfile, "r") as f:
                paths = filter(None, f.read().split("\n"))
            for path in paths:
                if n_connections >= config['num_flows']:
                    break
                proc = start_scion_flow(path, recv, n_connections)
                recv_processes.append(proc)
                n_connections += 1
            all_processes.append(recv_processes)

        print("All Calibrator flows running...")
        time.sleep(config["calibrator_duration"])
        print("Stopping Calibrator flows...")

        for recv_procs in all_processes:
            
            # TODO read out and store the achieve throughputs for each calibrator. store receiver wise (probably)
            for proc in recv_procs:
                proc.kill()
        print("Calibrator Flows Stopped.")

async def wait_for_all(processes):
    print(type(processes[0]))
    await asyncio.gather(*processes)
# Directly invoked from CLI
def build():
    print("Building with Bazel:")
    os.system("cd " + config["scion_location"] + " bazel build ...")


# Directly invoked from CLI
def exec_rtt():
    print("Invoking RTT Script:")
    rtt_run(config)


def exec_from_args():
    # global parser
    parser = argparse.ArgumentParser()
    FUNCTION_MAP = {
        "run_all": run_all,
        "runft": run_all_ft,
        "run": run_ft_experiment,
        "rtt": exec_rtt,
        "paths": get_paths,
        "probe": run_calibrators,
        "build": build,
        "setup": setup_sender,
        "listeners": start_tshark_and_listeners,
        "list_procs": list_procs,
        "kill_procs": kill_procs,
    }
    parser.add_argument("command", choices=FUNCTION_MAP.keys())
    parser.add_argument(
        "-n", action="store", dest="expname", default="default_experiment"
    )
    args = parser.parse_args()
    # global exp_time
    config["name"] = args.expname
    infer_config()
    if args.command not in ("list_procs", "kill_procs"):
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
    print("Resultfolder: ", config["result_dir"])
    return config["result_dir"]


def main(explicit_config=None):
    config = setup_configuration(explicit_config)
    rtt_run(config)
    run_ft_experiment()


if __name__ == "__main__":
    global config
    config = setup_configuration()
    exec_from_args()
