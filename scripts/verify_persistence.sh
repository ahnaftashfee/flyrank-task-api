#!/bin/sh
set -eu

base_url="http://localhost:${PORT:-8000}"
title="Persistence proof $(date +%s)"

echo "Creating task: $title"
curl --fail --silent --show-error \
  -X POST "$base_url/tasks" \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"$title\"}"
echo

echo "Stopping and recreating both containers without deleting the volume..."
docker compose down
docker compose up --build --detach

echo "Waiting for the API to become healthy..."
attempt=0
until curl --fail --silent "$base_url/health" >/dev/null; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    echo "API did not become healthy in time" >&2
    docker compose logs app db
    exit 1
  fi
  sleep 2
done

response=$(curl --fail --silent --show-error "$base_url/tasks")
printf '%s\n' "$response" | grep -F "$title" >/dev/null
echo "Persistence verified: the task is still present after container recreation."
