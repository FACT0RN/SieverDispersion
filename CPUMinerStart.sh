#!/bin/bash
IMAGE_NAME=sieverdispersion-cpu
DOCKERFILE_NAME=Dockerfile-cpu

git pull
sudo docker build -t $IMAGE_NAME -f $DOCKERFILE_NAME . || exit 1
sudo docker stop $(sudo docker ps -aq -f name=$IMAGE_NAME); sudo docker rm $(sudo docker ps -aq -f name=$IMAGE_NAME); sudo docker run --init -it --name $IMAGE_NAME $IMAGE_NAME
