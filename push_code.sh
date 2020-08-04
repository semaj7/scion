#!/bin/bash

IPS=(122.248.221.20 3.12.159.15 129.132.121.187)

for IP in "${IPS[@]}"
do
	echo "Folder check on $IP"
        ssh scionlab@${IP} 'mkdir -p /home/scionlab/go/src/github.com/scionproto/scion'
done

for IP in "${IPS[@]}"
do
	echo "Starting rsync on $IP"
        rsync -avz --exclude-from exclude-rsynch.txt -e ssh ~/go/src/github.com/scionproto/scion scionlab@${IP}:/home/scionlab/go/src/github.com/scionproto/scion 
done
