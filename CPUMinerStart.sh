#!/bin/bash
IMAGE_NAME=sieverdispersion-cpu
DOCKERFILE_NAME=Dockerfile-cpu

pushd -- "$(dirname "$0")"
git pull
./maybeGenerateMachineID.sh
sudo docker build -t $IMAGE_NAME -f $DOCKERFILE_NAME . || { popd; exit 1; }
sudo docker stop $(sudo docker ps -aq -f name=$IMAGE_NAME); sudo docker rm $(sudo docker ps -aq -f name=$IMAGE_NAME)
sudo docker run --init -it -e YAFU_THREADS=$YAFU_THREADS --name $IMAGE_NAME $IMAGE_NAME
popd
