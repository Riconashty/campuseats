#!/usr/bin/env bash
set -e

# CampusEats local PostgreSQL database starter
# Starts the PostgreSQL 16 container via Docker Compose and waits for readiness

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

echo "=================================================="
echo "Starting CampusEats PostgreSQL Database"
echo "=================================================="

# Check if docker CLI is available
if ! command -v docker >/dev/null 2>&1; then
    echo "Error: Docker is not installed or not in your PATH."
    echo "Please install Docker Desktop: https://www.docker.com/products/docker-desktop/"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info >/dev/null 2>&1; then
    echo "Error: Docker daemon is not running."
    echo "Please open/start Docker Desktop and try running this script again."
    exit 1
fi

# Start PostgreSQL container (supports existing container or docker compose)
if docker ps --format '{{.Names}}' | grep -q '^campuseats-db$'; then
    echo "PostgreSQL container 'campuseats-db' is already running."
elif docker ps -a --format '{{.Names}}' | grep -q '^campuseats-db$'; then
    echo "Starting existing container 'campuseats-db'..."
    docker start campuseats-db
else
    echo "Starting PostgreSQL via Docker Compose..."
    docker compose up -d db
fi

echo "Waiting for database to become ready..."
ATTEMPTS=0
MAX_ATTEMPTS=30

until docker exec campuseats-db pg_isready -U campuseats -d campuseats >/dev/null 2>&1 || [ ${ATTEMPTS} -eq ${MAX_ATTEMPTS} ]; do
    ATTEMPTS=$((ATTEMPTS + 1))
    sleep 1
done

if [ ${ATTEMPTS} -eq ${MAX_ATTEMPTS} ]; then
    echo "Warning: Database startup took longer than expected. Check container logs with 'docker compose logs db'."
    exit 1
fi

echo "=================================================="
echo "Database is ready on port 5432!"
echo "Database: campuseats | User: campuseats"
echo "You can now run: python run.py"
echo "To stop the database later, run: ./scripts/stop-db.sh"
echo "=================================================="
