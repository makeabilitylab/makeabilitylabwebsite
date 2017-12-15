#!/bin/bash

#first build the image
cd ..
docker build -t $1 .

#if there is an existing container, stop it
ISRUNNING=$(docker ps | grep $1)
if [ -n "$ISRUNNING" ]; then
        docker stop $1
fi

#if there is a stopped container, remove it
ISDEAD=$(docker ps --all | grep $1)
if [ -n "$ISDEAD" ]; then
        docker rm $1
fi

#finally, instantiate the new container
cd $1
/bin/bash < command

