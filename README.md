# CampusEats

CampusEats connects campus food vendors that have leftover food with students who want it, reducing food waste and hunger on campus.

---

## Running with Docker Compose

The entire application (Flask web server + PostgreSQL database) can be started with a single command from the repository root:

#### First Time:
```bash
docker compose up --build
```

#### All Other Times:
```bash
docker compose up
```

Once started, open `http://localhost:5001` in your browser.

### Automatic Seed Accounts
On first launch, the database automatically initializes the schema and creates demo accounts for grading:
- **Vendor Account:**
  - Email: `vendor@campuseats.edu`
  - Password: `Vendor123!`
- **Student Account:**
  - Email: `student@campuseats.edu`
  - Password: `Student123!`

---

## Docker Commands Cheatsheet

### 1. Attached Mode (Foreground / Live Logs)
In attached mode, your terminal stays connected to the container output. You can see real-time HTTP requests, database logs, and application print statements.

- **Start attached and rebuild:**
  ```bash
  docker compose up --build
  ```
- **Stop and exit:**
  Press `Ctrl + C`. Docker will gracefully stop both the web and database containers.

---

### 2. Detached Mode (Background)
In detached mode (`-d`), Docker starts the containers in the background and immediately frees up your terminal for other commands.

- **Start detached in background:**
  ```bash
  docker compose up -d --build
  ```
- **Check container status:**
  ```bash
  docker compose ps
  ```
- **View live logs (follow output):**
  ```bash
  docker compose logs -f
  ```
- **View logs for only the web app:**
  ```bash
  docker compose logs -f web
  ```
- **View logs for only the database:**
  ```bash
  docker compose logs -f db
  ```
- **Stop background containers:**
  ```bash
  docker compose down
  ```
- **Stop containers and delete database volume (fresh start):**
  ```bash
  docker compose down -v
  ```

---

### 3. Running Commands Inside Containers
- **Open an interactive Bash shell inside the Flask container:**
  ```bash
  docker compose exec web bash
  ```
- **Open an interactive PostgreSQL console:**
  ```bash
  docker compose exec db psql -U campuseats -d campuseats
  ```

---

## Alternative: Local Python Development (Without Full Docker)

If you prefer to run Flask directly on your host machine while containerizing only PostgreSQL:

### 1. Clone the Repository
```bash
git clone git@github.com:Riconashty/campuseats.git
cd campuseats
```

### 2. Create and Activate Virtual Environment
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

### 6. Start the PostgreSQL Container
```bash
./scripts/start-db.sh
```

### 7. Run the Application
```bash
python run.py
```
Open `http://localhost:5001` in your browser. When finished, stop the database with:
```bash
./scripts/stop-db.sh
```

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

---

## Automated Black Box Testing (Selenium - US1)

As required by the project specifications, an automated black box browser test is implemented for **User Story 1 (User Registration and Authentication)** in `tests/integration/test_us1_selenium.py`.

### What the Test Covers
The test suite drives **Google Chrome in headless mode** against a live application deployment without directly invoking any internal Python application functions:
- **AC 1 (Registration):** Valid student and vendor account creation, form submissions, and redirects to `/login` with success flash banners.
- **AC 2 (Duplicate Email):** Rejection of duplicate email addresses with error message `"An account with that email already exists."`.
- **AC 3 (Form Validation):** Missing required fields and password length constraints (< 8 characters).
- **AC 4 (Invalid Authentication):** Incorrect password and nonexistent email login attempts showing `"Invalid email or password."`.
- **AC 5 (Authentication & Logout Flow):** Valid login, role-specific navigation updates showing the user's name and role in the navbar, and session destruction on logout.
- **AC 6 (Seed Account Login):** Direct authentication with pre-seeded vendor credentials.

### How to Run the Selenium Suite

#### 1. Start the Live Application
Start the application using Docker Compose (Recommended):
```bash
docker compose up
```
*(Or start locally with `./scripts/start-db.sh && python run.py`)*

#### 2. Execute the Automated Runner
In a separate terminal window:
```bash
./scripts/run-selenium.sh
```

Alternatively, you can run pytest directly:
```bash
pytest tests/integration/test_us1_selenium.py --no-cov -v -s
```

> [!NOTE]
> When the web server is offline (such as during standard local `./scripts/verify.sh` runs), the Selenium tests automatically detect the offline state, print a helpful diagnostic message, and skip gracefully without failing the build or test coverage gate.

