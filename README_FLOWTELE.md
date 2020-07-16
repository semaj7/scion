# FlowTele Project with SCION

## Dependencies

- parallel ssh, `pip install parallel-ssh`


## Outline

- On each machine, start iperf server
- On each machine, start `perf` for collecting SRTT
- On each machine, start one iperf client for each neighbor
