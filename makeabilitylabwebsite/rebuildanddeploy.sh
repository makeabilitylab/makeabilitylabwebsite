#!/bin/bash

PROD_HOST=grabthar
TEST_HOST=docker-test2

#navigate to the root directory
cd ../

#if we're on a test system, lets mount the test volume
if [[ $(hostname -s) == $TEST_HOST ]] ; then
   export DJANGO_ENV=TEST
   export MEDIA_PATH=/cse/web/research/makelab/www-test
   export CONFIG_PATH=/cse/web/research/makelab/secret/config-test.ini
   export POSTGRES_IMAGE=postgres:16
   export POSTGRES_VOLUME=postgres16-data
elif [[ $(hostname -s) == $PROD_HOST ]] ; then
   export DJANGO_ENV=PROD
   export MEDIA_PATH=/cse/web/research/makelab/www
   export CONFIG_PATH=/cse/web/research/makelab/secret/config.ini
   export POSTGRES_IMAGE=postgres:16
   export POSTGRES_VOLUME=postgres16-data
else
   export DJANGO_ENV=DEBUG
fi

docker compose build website
docker compose up -d
