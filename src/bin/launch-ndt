#!/bin/bash

cd /home/ubuntu/ndt-server/

docker run --rm -d --network=host        \
      --volume `pwd`/certs:/certs:ro      \
      --volume `pwd`/datadir:/datadir     \
      --read-only                            \
      --user `id -u`:`id -g`                 \
      --cap-drop=all                         \
      ndt7       \
      -cert /certs/cert.pem                  \
      -key /certs/key.pem                    \
      -datadir /datadir                      \
      -ndt7_addr 192.168.1.5:4443          \
      -ndt5_addr 192.168.1.5:3001          \
      -ndt5_wss_addr 192.168.1.5:3010      \
      -ndt7_addr_cleartext 192.168.1.5:8080
           

