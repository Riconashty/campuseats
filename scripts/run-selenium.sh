#!/bin/bash
set -e

# Target endpoint: the Docker Compose deployment unless BASE_URL says otherwise
# (for example BASE_URL=http://localhost:5001 when running `python run.py` directly)
export BASE_URL="${BASE_URL:-http://localhost:5000}"

# This script is the end-to-end run, so the tests must really run: with E2E_REQUIRED set,
# an unreachable app or a browser that will not start is a failure, not a skip
export E2E_REQUIRED=1

echo "======================================================================"
echo " CampusEats Selenium Automated Black Box Test Runner"
echo " Target Endpoint: $BASE_URL"
echo "======================================================================"

# Activate virtual environment if available
if [ -d ".venv" ]; then
    echo "Activating virtual environment (.venv)..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "Activating virtual environment (venv)..."
    source venv/bin/activate
fi

# Check whether the web server is responding
echo "Checking server status at $BASE_URL..."
if curl --silent --fail --max-time 5 "$BASE_URL/health/db" > /dev/null; then
    echo "Server is UP and reachable."
    echo "Starting Selenium black box test suite (Headless Chrome)..."
    echo ""
    python -m pytest tests/integration/ --no-cov -v -rs
    echo ""
    echo "======================================================================"
    echo " Selenium tests completed successfully!"
    echo "======================================================================"
else
    echo ""
    echo "======================================================================"
    echo " ERROR: CampusEats server is NOT running at $BASE_URL"
    echo "======================================================================"
    echo "Selenium tests require a live running application deployment."
    echo ""
    echo "To start the application:"
    echo "  Docker Compose (Recommended):"
    echo "    docker compose up --build"
    echo ""
    echo "  Local Development Server (listens on port 5001):"
    echo "    ./scripts/start-db.sh && python run.py"
    echo "    BASE_URL=http://localhost:5001 ./scripts/run-selenium.sh"
    echo ""
    echo "After starting the server, run this script again:"
    echo "  ./scripts/run-selenium.sh"
    echo "======================================================================"
    exit 1
fi
