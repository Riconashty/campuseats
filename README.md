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
| UML Architecture | Domain class diagram & sequence diagrams | [uml/class.wsd](uml/class.wsd), [uml/sequence-US1.wsd](uml/sequence-US1.wsd), [uml/sequence-US4.wsd](uml/sequence-US4.wsd) |
| Manual Test Record | Every acceptance criterion tested by hand, with tester, date, and result | [tests/manual-tests.md](tests/manual-tests.md) |

## Testing

Testing was done through a mix of automated gates and manual verification at each step of development:

- **Local Verification Gate (`./scripts/verify.sh`):** Before committing or opening a PR, developers ran `./scripts/verify.sh`. This runs Ruff formatting, Ruff linting, and the pytest test suite, enforcing a strict minimum of 80% code coverage.
- **GitHub Actions CI (`.github/workflows/ci.yml`):** Every push and pull request targeting `dev` or `main` triggers GitHub Actions CI. It spins up an environment and runs the exact same checks (format, lint, and coverage gate) to prevent broken code from being merged.
- **Selenium Automated Black Box Test (US4):** Our automated story is US4, Reserve portions. Headless Chrome drives the running Docker Compose deployment through every US4 acceptance criterion, including two students reserving the last portion at the same moment. It is run with `./scripts/run-selenium.sh` once the app is up, and by the `e2e` job in GitHub Actions. See [Automated Black Box Testing](#automated-black-box-testing-selenium).
- **PostgreSQL Tests (`tests/postgres`):** The unit tests use in-memory SQLite, which has no row locks and no column length limits. These tests run the same routes against real PostgreSQL to check that concurrent requests cannot corrupt inventory or reservation status.
- **Manual Tests:** Every acceptance criterion of every other story is tested by hand and recorded in [tests/manual-tests.md](tests/manual-tests.md).
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

The vendor account starts with four sample listings whose pickup windows are open for the next 2 to 4 hours. If the app is restarted after all listings have ended, a fresh set of sample listings is posted so the student feed is not empty; the ended ones are kept as they were.

To start again from an empty database:
```bash
docker compose down -v
docker compose up --build
```

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

Our automated story is **US4: Reserve portions**. The test in `tests/integration/test_us4_selenium.py` drives the live application through headless Google Chrome. It never imports the application's Python code or touches the database: it registers its own vendor and students on the Register page, posts its own listings, and reads results from the pages a user would see.

### Running the Test
Requirements: Google Chrome, and the development dependencies (`pip install -r requirements-dev.txt`).

1. Start the deployment:
   ```bash
   docker compose up --build
   ```
2. In a second terminal, from the repository root:
   ```bash
   ./scripts/run-selenium.sh
   ```

The script targets `http://localhost:5000`. To test a different address, set `BASE_URL`:
```bash
BASE_URL=http://localhost:5001 ./scripts/run-selenium.sh
```

The script fails if the app is unreachable or Chrome cannot start, so a passing run always means the tests really ran. When the tests are collected as part of the unit test gate (`./scripts/verify.sh`) and the app is not running, they are skipped instead.

The test cancels the listings it posted when it finishes. Its test accounts stay in the database; `docker compose down -v` removes them.

### What It Covers

| US4 acceptance criterion | How the test checks it |
| --- | --- |
| 1. Reserving 1 or 2 portions stores a reservation, lowers remaining portions by that amount, and shows a unique 6-character pickup code | One student reserves 2 portions and another reserves 1 from a 5-portion listing. After each, the card's remaining count drops by exactly that amount, the code has 6 characters, the reservation is on My Reservations, the two codes differ, and the vendor's My Listings shows 3 reserved and 2 remaining. |
| 2. Requesting more portions than remain creates no reservation and shows an error | A student asks for 2 portions of a 1-portion listing. The error appears, the count stays at 1, and My Reservations has no entry. |
| 3. A student who already holds an active reservation is told so | A student reserves, then reserves the same listing again. The message appears and there is still exactly one reservation. |
| 4. When two students reserve the last portion at the same moment, only one succeeds | Two separate browsers, logged in as different students, click Reserve on a 1-portion listing at the same instant, three times over. Each time exactly one gets a pickup code, the other gets the error, and the vendor sees 1 reserved and 0 remaining. |

`tests/integration/test_us1_selenium.py` is kept as extra regression coverage for registration and login. US1 is still tested by hand in `tests/manual-tests.md`.

---

## PostgreSQL Tests

With PostgreSQL running (`docker compose up` or `./scripts/start-db.sh`) and `TEST_DATABASE_URL` set as in `.env.example`:
```bash
python -m pytest tests/postgres --no-cov -v
```
These create the `campuseats_test` database if it does not exist and never touch the main `campuseats` database. They are skipped when PostgreSQL is not reachable.
