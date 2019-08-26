#!/bin/bash

#navigate to the root directory
cd ../

#First, build the website image
docker-compose build website

#second bring up any containers that are down, recreating any that have a newer image.
docker-compose up -d
