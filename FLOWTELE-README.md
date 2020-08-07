
# Flowtele + SCION

Flowtele scripts are in `ft-scripts/`

Use
        `source aliases.sh`
to load useful shortcuts.

## RTT Experiments

Workflow:

```
rtt topo
rtt server
rtt sensor
rtt run
rtt kill
rtt preprocess
rtt parse
rtt kill
rtt clean
```
 or simply

 `rtt run_all`


## RTT Requirements

- Ubuntu. Tested on 18 and 20.
- perf, which requires linux kernel at least kernel 4.15.0. http://manpages.ubuntu.com/manpages/bionic/man1/perf.1.html
- iperf3, version 3.7 installed with
    ```
    sudo apt remove iperf3 libiperf0
    sudo apt install libsctp1
    wget https://iperf.fr/download/ubuntu/libiperf0_3.7-3_amd64.deb
    wget https://iperf.fr/download/ubuntu/iperf3_3.7-3_amd64.deb
    sudo dpkg -i libiperf0_3.7-3_amd64.deb iperf3_3.7-3_amd64.deb
    rm libiperf0_3.7-3_amd64.deb iperf3_3.7-3_amd64.deb
    ```
- python3. tested on 3.69 or higher. pip3 and some librairies
    ```
    sudo apt install python3-pip
    sudo python3 -m pip install numpy matplotlib PyYAML

    ```

## RTT Access

The scripts will use sudo commands for:

- `sudo perf record`
- `sudo perf report`
- `sudo ethtool --offload *some_interface* tso *on/off*`
- `sudo iperf3`
- `sudo kill *process*` for processes that are included in file created by these scripts. (Might be problematic)
- `sudo pkill *iperf3/perf*`
