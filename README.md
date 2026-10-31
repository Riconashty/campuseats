# CampusEats

CampusEats connects campus food vendors that have leftover food with students who want it, reducing food waste and hunger on campus.

---

## How to Run Locally

### 1. Clone the Repository
```bash
git clone git@github.com:Riconashty/campuseats.git
cd campuseats
```

### 2. Create and Activate Virtual Environment
- Check `pyproject.toml` for the Python version used.
```bash
python3 -m venv .venv
```
- **macOS / Linux:** `source .venv/bin/activate`
- **Windows:** `.venv\Scripts\activate`

### 3. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .
```

### 4. Set Up Pre-Commit Guardrails
Install git hooks so formatting and style checks run automatically before every commit:
```bash
pre-commit install
```

### 5. Create Environment Configuration
```bash
cp .env.example .env
```

### 6. Run the Application
```bash
python run.py
```
Open `http://localhost:5000` in your browser.

---

## Development & Verification Workflow

To prevent broken or untested code from reaching `dev` and `main`, automated guardrails run both locally and in GitHub Actions.

### Before You Commit or Push
Always run the verification gate:
```bash
./scripts/verify.sh
```
This runs three checks in sequence:
- **Code formatting** via Ruff
- **Linting & code quality** via Ruff
- **Unit test suite & code coverage** (minimum 80% threshold required) via Pytest

#### If verification fails:
- **Formatting issue:** Run `ruff format .` to reformat automatically.
- **Linting issue:** Run `ruff check --fix .` to auto-fix common problems.
- **Test / coverage failure:** Fix the failing test or add test cases to meet the 80% coverage requirement.

### Automated CI in GitHub
When you push or open a pull request targeting `dev` or `main`:
- GitHub Actions automatically runs the formatting check, linter, and full test suite with coverage enforcement.
- Merges are gated on all checks passing.

### Individual Commands Cheatsheet
```bash
# Run unit tests and view coverage report
pytest

# Check code formatting
ruff format --check .

# Automatically reformat files
ruff format .

# Run linter
ruff check .

# Run linter with auto-fix
ruff check --fix .
```
