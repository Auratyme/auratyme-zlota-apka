docker volume remove auratyme_schedules-db-data
docker compose up -d --build

docker exec -it auratyme-schedules-1 npm run db:generate
docker exec -it auratyme-schedules-1 npm run db:migrate

docker compose restart schedules
docker compose restart api-gateway