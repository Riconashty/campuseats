#!/usr/bin/env bash
set -e

# CampusEats local verification gate
# Runs formatting checks, linting, and automated tests with code coverage enforcement

echo "=================================================="
echo "CampusEats Verification Gate"
echo "=================================================="

# Ensure script runs from the repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

# Activate virtual environment if present and not already activated
if [ -z "${VIRTUAL_ENV}" ]; then
  if [ -d ".venv" ]; then
    echo "Activating virtual environment (.venv)..."
    source .venv/bin/activate
  elif [ -d "venv" ]; then
    echo "Activating virtual environment (venv)..."
    source venv/bin/activate
  fi
fi

# Track overall verification status
STATUS=0

echo ""
echo "Running code formatting check..."
if ruff format --check .; then
  echo "Formatting check passed."
else
  echo "Formatting issues detected. Run 'ruff format .' to automatically reformat."
  STATUS=1
fi

echo ""
echo "Running linting and code quality check..."
if ruff check .; then
  echo "Linting checks passed."
else
  echo "Linting issues detected. Run 'ruff check --fix .' to automatically fix common issues."
  STATUS=1
fi

echo ""
echo "Running automated test suite with coverage enforcement (min 80%)..."
if pytest; then
  echo "All tests passed and minimum 80% coverage requirement met."
else
  echo "Tests failed or code coverage threshold not met."
  STATUS=1
fi

echo ""
echo "=================================================="
if [ ${STATUS} -eq 0 ]; then
  echo "Verification PASSED: Code is clean and ready to commit/push."
  echo "=================================================="
  exit 0
else
  echo "Verification FAILED: Please address the issues listed above."
  echo "=================================================="
  exit 1
fi
