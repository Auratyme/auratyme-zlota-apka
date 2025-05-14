#!/bin/bash
# Script to monitor scheduler logs in the Docker container

# Get the container ID
CONTAINER_ID=$(docker ps | grep schedules-ai | awk '{print $1}')

if [ -z "$CONTAINER_ID" ]; then
    echo "Nie znaleziono kontenera schedules-ai. Upewnij się, że kontener jest uruchomiony."
    exit 1
fi

echo "Monitorowanie logów schedulera w kontenerze $CONTAINER_ID..."
echo "Naciśnij Ctrl+C, aby zakończyć."

# Monitor the scheduler log file
docker exec -it $CONTAINER_ID tail -f /app/scheduler.log
