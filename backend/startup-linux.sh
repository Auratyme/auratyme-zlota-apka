#!/bin/sh

docker compose up -d --build

if [ $? -ne 0 ]
then
  docker exec -it auratyme-schedules-1 npx drizzle-kit push --force
  docker compose restart schedules notifications api-gateway
  docker exec -it auratyme-notifications-1 npx drizzle-kit push --force
fi