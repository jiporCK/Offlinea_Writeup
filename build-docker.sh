#!/bin/bash
docker rm -f offlinea
docker build -t offlinea . && \
docker run --init --name=offlinea --rm -p 8000:8000 -it offlinea