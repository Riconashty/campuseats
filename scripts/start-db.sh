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
    echo "Error: Database startup took longer than expected. Check container logs with 'docker compose logs db'."
    exit 1
fi

echo "Verifying database user credentials and connectivity..."
DB_USER="${POSTGRES_USER:-campuseats}"
DB_PASSWORD="${POSTGRES_PASSWORD:-devpassword}"
DB_NAME="${POSTGRES_DB:-campuseats}"

AUTH_ATTEMPTS=0
MAX_AUTH_ATTEMPTS=5
AUTH_OK=false
AUTH_OUTPUT=""

while [ ${AUTH_ATTEMPTS} -lt ${MAX_AUTH_ATTEMPTS} ]; do
    if AUTH_OUTPUT=$(docker exec -e PGPASSWORD="${DB_PASSWORD}" campuseats-db psql -U "${DB_USER}" -d "${DB_NAME}" -tAc "SELECT 1;" 2>&1); then
        if [ "${AUTH_OUTPUT}" = "1" ]; then
            AUTH_OK=true
            break
        fi
    fi
    AUTH_ATTEMPTS=$((AUTH_ATTEMPTS + 1))
    sleep 1
done

if [ "${AUTH_OK}" = false ]; then
    echo ""
    echo "=================================================="
    echo "Error: Database authentication check failed!"
    echo "=================================================="
    echo "The PostgreSQL service is running, but user '${DB_USER}' cannot connect"
    echo "to database '${DB_NAME}' with the configured credentials."
    echo ""
    echo "PostgreSQL reported:"
    echo "  ${AUTH_OUTPUT}"
    echo ""
    echo "This usually happens when an older container was initialized with"
    echo "different credentials or volume data."
    echo ""
    echo "To remove the conflicting container and start fresh with proper credentials:"
    echo "  docker rm -f campuseats-db"
    echo "  ./scripts/start-db.sh"
    echo "=================================================="
    exit 1
fi

echo "=================================================="
echo "Database is ready on port 5432!"
echo "Database: ${DB_NAME} | User: ${DB_USER}"
echo "You can now run: python run.py"
echo "To stop the database later, run: ./scripts/stop-db.sh"
echo "=================================================="
