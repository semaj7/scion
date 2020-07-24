#!/bin/python3

# Unclear if needed. Maybe rather use ansible or cssh

from __future__ import print_function

from pssh.clients import ParallelSSHClient

client = ParallelSSHClient(['localhost'])
output = client.run_command('whoami')
for line in output['localhost'].stdout:
    print(line)

