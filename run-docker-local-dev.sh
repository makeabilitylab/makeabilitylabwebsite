#!/bin/bash

if [ "$1" == "--help" ]; then
  echo "Usage: $0 [OPTION]..."
  echo "Run local development environment in Docker."
  echo ""
  echo "Options:"
  echo "--build     Build the Docker image before starting the services."
  echo "--help      Display this help and exit."
  exit
fi

if [ "$1" == "--build" ]
then
    docker build . -t makelab_image
fi

docker-compose -f docker-compose-local-dev.yml up
