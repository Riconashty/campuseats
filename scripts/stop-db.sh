#!/usr/bin/env bash
set -e

# CampusEats local PostgreSQL database stopper
# Stops the PostgreSQL container cleanly

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

echo "Stopping CampusEats PostgreSQL container..."
if docker ps --format '{{.Names}}' | grep -q '^campuseats-db$'; then
    docker stop campuseats-db
fi
echo "Database stopped. To start again, run: ./scripts/start-db.sh"
