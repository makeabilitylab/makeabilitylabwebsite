#!/bin/bash

#navigate to the root directory
cd ../

#if we're on a test system, lets mount the test volume
if [[ $(hostname -s) == *"test"* ]] ; then
   export DJANGO_ENV=TEST
   docker-compose -f docker-compose.yml -f docker-compose-test.yml build website
   docker-compose -f docker-compose.yml -f docker-compose-test.yml up -d
else
   export DJANGO_ENV=PROD
   docker-compose -f docker-compose.yml -f docker-compose-prod.yml build website
   docker-compose -f docker-compose.yml -f docker-compose-prod.yml up -d
fi
