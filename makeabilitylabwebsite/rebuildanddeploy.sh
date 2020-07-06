#!/bin/bash

#navigate to the root directory
cd ../

#if we're on a test system, lets mount the test volume
if [[ $(hostname -s) == *"test"* ]] ; then
   sed -i 's,makelab/www:,makelab/www-test:,' docker-compose.yml
fi

#First, build the website image
docker-compose build website

#second bring up any containers that are down, recreating any that have a newer image.
docker-compose up -d
