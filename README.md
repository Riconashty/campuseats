# CampusEats

CampusEats connects campus food vendors that have leftover food with students who want it, reducing food waste and hunger on campus.

---

## Team
- [Tyler Black](https://github.com/khakis23)
- [Riley Drenth](https://github.com/RileyDrenthMSU)
- [Cameron Greeson](https://github.com/GreesonC)
- [Richard Hall](https://github.com/Riconashty)
- [Stephanie Rivera-Martinez](https://github.com/FrostyBagels)

### SCRUM Master
[Riley Drenth](https://github.com/RileyDrenthMSU)

---

## SCRUM Documents

The team followed a SCRUM methodology to manage the development of this project.
Below lists the documents that show the development process.

| Document | Description | Link |
| --- | --- | --- |
| Sprint Planning & Release Plan | Backlog scoring, velocity, and sprint goals | [SPRINT_PLANNING.md](scrum/SPRINT_PLANNING.md) |
| Daily Standups | Asynchronous Discord standup logs | [DAILY_STANDUPS.md](scrum/DAILY_STANDUPS.md) |
| Reviews & Retrospectives | Sprint 1–4 reviews and Sprint 1–3 retrospectives | [REVIEWS_AND_RETROSPECTIVES.md](scrum/REVIEWS_AND_RETROSPECTIVES.md) |
| Sprint Boards | Exported Jira boards for all sprints | [all_sprint_boards.pdf](scrum/sprint_boards/all_sprint_boards.pdf) |
| Burndown Chart | Project release burndown chart and metrics | [burndown.png](scrum/burndown.png) |
| UML Architecture | Domain class diagram & sequence diagram | [uml/class.wsd](uml/class.wsd), [uml/sequence-US1.wsd](uml/sequence-US1.wsd) |

## Testing

Testing was done through a mix of automated gates and manual verification at each step of development:

- **Local Verification Gate (`./scripts/verify.sh`):** Before committing or opening a PR, developers ran `./scripts/verify.sh`. This runs Ruff formatting, Ruff linting, and the pytest test suite, enforcing a strict minimum of 80% code coverage.
- **GitHub Actions CI (`.github/workflows/ci.yml`):** Every push and pull request targeting `dev` or `main` triggers GitHub Actions CI. It spins up an environment and runs the exact same checks (format, lint, and coverage gate) to prevent broken code from being merged.
- **Selenium Automated Black Box Tests:** End-to-end browser tests run headless Chrome against the running Docker container to test full user stories through the UI (US1 auth and US4 reservations). These can be run anytime using `./scripts/run-selenium.sh` once the app is up.
- **PR Reviewer Verification:** PRs required approval from a teammate other than the author before merging into `dev`. Reviewers pulled the branch, checked the code, ran the app locally, and walked through the changes in the browser to verify they worked.
- **End-of-Sprint Manual Testing:** At the end of each sprint before creating releases, we started the full Docker Compose stack from scratch and re-tested all implemented user stories end-to-end.


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

Once started, open `http://localhost:5000` (or `http://localhost:5001`) in your browser.

### Automatic Seed Accounts
On first launch, the database automatically initializes the schema and creates demo accounts for grading (enabled by default in Docker and `.env.example` via `SEED_DEMO_USERS=true`):
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

When you're finished, stop the database container with:
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

## Automated Black Box Testing (Selenium)

Automated end-to-end browser tests drive the live application through headless Google Chrome without calling internal Python code directly.

### Running the Tests
With the application running (`docker compose up` or `python run.py`), execute:
```bash
./scripts/run-selenium.sh
```
*(Or directly via pytest: `pytest tests/integration/test_us1_selenium.py --no-cov -v`)*

> [!NOTE]
> If the live server is offline (e.g. during `./scripts/verify.sh`), Selenium tests skip gracefully without failing the test run or coverage gate.

### Covered Stories
- **US1 (Registration & Login):** Validates account creation (student & vendor), duplicate email rejection, validation constraints, invalid credentials, navbar role states, and logout.
- *Additional user story test suites will be added here as subsequent stories are completed.*

