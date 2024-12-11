#!/bin/bash
set -e
IMAGE_NAME=sieverdispersion-cpu
DOCKERFILE_NAME=Dockerfile-cpu

pushd -- "$(dirname "$0")"
git pull
./maybeGenerateMachineID.py
sudo docker pull ghcr.io/fact0rn/sieverdispersion:sieverdispersion-base-cpu
sudo docker build -t $IMAGE_NAME -f $DOCKERFILE_NAME . || { popd; exit 1; }
sudo docker stop $(sudo docker ps -aq -f name=$IMAGE_NAME) || true
sudo docker rm $(sudo docker ps -aq -f name=$IMAGE_NAME) || true
sudo docker run --init -it -e YAFU_THREADS=$YAFU_THREADS -e HAS_AVX512=False --name $IMAGE_NAME $IMAGE_NAME
popd
