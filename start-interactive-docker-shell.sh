#!/bin/bash

# Define the compose file and service name from your configuration
COMPOSE_FILE="docker-compose-local-dev.yml"
SERVICE_NAME="website"

# Check if the container is actually running
# We use 'ps -q' to get the container ID. If it's empty, the service is down.
if [ -z "$(docker-compose -f $COMPOSE_FILE ps -q $SERVICE_NAME)" ]; then
    echo "Error: The '$SERVICE_NAME' container is not running."
    echo "Please start your environment first: docker-compose -f $COMPOSE_FILE up"
    exit 1
fi

# Inform the user
echo "Opening interactive shell for '$SERVICE_NAME'..."

# Execute bash inside the running container
docker-compose -f $COMPOSE_FILE exec $SERVICE_NAME bash