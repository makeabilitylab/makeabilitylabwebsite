#!/bin/bash

if [ "$1" == "--help" ]; then
  echo "Usage: $0 [OPTION]..."
  echo "Run local development environment in Docker."
  echo ""
  echo "Options:"
  echo "--build     Build the Docker image before starting the services."
  echo "--buildnc   Build the Docker image without cache before starting the services."
  echo "--verbose   Build the Docker image with verbose output."
  echo "--help      Display this help and exit."
  exit
fi

VERBOSE=false
BUILD=false
BUILDNC=false

for arg in "$@"
do
    if [ "$arg" == "--verbose" ]; then
        VERBOSE=true
    elif [ "$arg" == "--build" ]; then
        BUILD=true
    elif [ "$arg" == "--buildnc" ]; then
        BUILDNC=true
    fi
done

if [ "$VERBOSE" = true ] && [ "$BUILD" = true ]; then
    echo "Building Docker image with verbose output... log file stored in docker_makelab_build.log"
    docker build --progress=plain . -t makelab_image 2>&1 | tee docker_makelab_build.log
elif [ "$VERBOSE" = true ] && [ "$BUILDNC" = true ]; then
echo "Building Docker image with --no-cache and verbose output... log file stored in docker_makelab_build.log"
    docker build --no-cache --progress=plain . -t makelab_image 2>&1 | tee docker_makelab_build.log
elif [ "$BUILD" = true ]; then
    docker build . -t makelab_image
elif [ "$BUILDNC" = true ]; then
    echo "Building docker image with --no-cache..."
    docker build --no-cache . -t makelab_image
fi

docker compose -f docker-compose-local-dev.yml up
