#!/bin/bash
set -e

# Target endpoint (default to 5001 or respect BASE_URL environment variable)
BASE_URL="${BASE_URL:-http://localhost:5001}"

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
if curl --silent --fail --max-time 2 "$BASE_URL/" > /dev/null; then
    echo "Server is UP and reachable."
    echo "Starting Selenium black box test suite (Headless Chrome)..."
    echo ""
    pytest tests/integration/test_us1_selenium.py --no-cov -v -s
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
    echo "    docker compose up"
    echo ""
    echo "  Local Development Server:"
    echo "    ./scripts/start-db.sh && python run.py"
    echo ""
    echo "After starting the server, run this script again:"
    echo "  ./scripts/run-selenium.sh"
    echo "======================================================================"
    exit 1
fi
