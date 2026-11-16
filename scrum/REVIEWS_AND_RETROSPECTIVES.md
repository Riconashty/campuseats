# CampusEats: Sprint Reviews & Retrospectives

---

# Sprint 1 (Setup, Environment & US1)

## Sprint 1 Review
* **Date:** Saturday, Nov 1, 2026
* **Attendees:** Tyler, Richard, Riley (SM), Steph, Cameron
* **Goal:** Repo scaffolding, local dev setup, PlantUML diagrams, DB setup, and US1 (Register & Log In).

### Completed Work & Demos
* **Setup & Architecture:**
  * `SCRUM-5` (PR #13): UML class diagram committed to `uml/class.wsd`.
  * `SCRUM-6` (PR #13): Sequence diagram for auth in `uml/sequence-US1.wsd`.
  * `SCRUM-10` (PR #10): Local venv setup, `.gitignore`, `.env.example`, and requirements.
  * `SCRUM-11`: GitHub setup, branch protections, and Discord branching guide.
  * `SCRUM-12` (PR #14): Flask app factory (`create_app`), config, base template, and run script.
  * `SCRUM-13` (PR #17): PostgreSQL setup with Flask-SQLAlchemy and auto-schema init.
  * `SCRUM-31` (PR #26): CI verification script (`scripts/verify.sh`) with Ruff lint/format and 80% coverage check.
* **User Story 1 (Register & Log In) — Passing in Docker:**
  * `SCRUM-24` (PR #15): User registration with hashed passwords. Rejects duplicate emails and empty fields with flash alerts.
  * `SCRUM-25` (PR #16): Flask-Login session management and role-based redirects (Students $\rightarrow$ `/listings`, Vendors $\rightarrow$ `/vendor/listings`). Navbar reflects auth state.
* **Carried to Sprint 2:**
  * `SCRUM-27` (US2 Post Listing): Started backend on branch, moving to Sprint 2.

---

## Sprint 1 Retrospective (Meeting 2)
* **Date:** Saturday, Nov 1, 2026
* **Attendees:** Tyler, Richard, Riley, Steph, Cameron

### What Worked
* Flask app factory and Postgres setup went smoothly.
* Adding `./scripts/verify.sh` early caught formatting and syntax issues before PRs were opened.
* Good initial momentum on Sprint 0 tasks.

### What Didn't Work
* People starting new tickets before reviewing open PRs, creating review bottlenecks.
* Some PRs had poor descriptions, making testing unclear.
* Branching without linking to a GitHub issue or checking Jira first.
* Tickets worked out of order from the sprint map.

### Action Items for Sprint 2
* GH issues must be worked "in-order" according to the sprint map.
* Review other work before starting on a new ticket (Review-First rule).
* PR formatting template: Summary, Changes made, step-by-step How to review.
* Review formatting template: Things working / did well, Issues/findings, Approve or Request changes.
* Avoid creating branches without linking to a GH issue; check Jira first!
* Utilize Draft PRs for unfinished work.

---

# Sprint 2 (US2, US3, US4, US6 & Docker/Testing)

## Sprint 2 Review
* **Date:** Sunday, Nov 8, 2026
* **Attendees:** Tyler, Richard, Riley, Steph, Cameron
* **Goal:** Docker Compose deployment, Selenium tests, US2 (Post Listings), US3 (Browse Listings), US4 (Reserve Portions), and US6 (My Reservations).

### Completed Work & Demos
* **Docker & Testing:**
  * `SCRUM-15` (PR #32, #33): Multi-service `docker-compose.yml` (Flask + PostgreSQL 16 on port 5001) with healthchecks.
  * `SCRUM-32` (PR #33): Headless Chrome Selenium test suite for US1 running against live Docker container.
* **User Stories Implemented & Passing:**
  * `SCRUM-27` (PR #31) — US2 Post Listing: Vendors can post surplus food (1–100 portions), tags, location, and validated pickup window. Role-guarded.
  * `SCRUM-16` (PR #34) — US3 Browse Listings: Students see available listings sorted by soonest ending pickup window, with remaining portions.
  * `SCRUM-29` (PR #35) — US4 Reserve Portions: Atomic portion reservation with 6-char pickup code modal. Rejects overselling and duplicate active reservations.
  * `SCRUM-20` (PR #39) — US6 My Reservations: Student dashboard showing reservations with status badges and cancel action that returns portions.

---

## Sprint 2 Retrospective (Meeting 3)
* **Date:** Sunday, Nov 8, 2026
* **Attendees:** Tyler, Richard, Riley, Steph, Cameron

### Previous Action Items Status (from Sprint 1 Retro)
* **PR Template with "How to review":** Carried out! PRs #31, #33, #34, and #35 used the template, which made testing much easier.
* **Review other work before starting new tickets:** Carried out. Team reviews were much faster and more detailed.
* **Link branches to GH issues / Draft PRs:** Partially carried out, but Jira subtask syncing was annoying.

### What Worked
* Great reviews across the team.
* "Road maps" posted in the `#sprint-schedule` Discord channel kept everyone aligned.
* Discord updates (e.g. *"branch-name is ready for review!"*) kept PRs moving.
* Creating "tech-debt" tickets for minor issues so dependent tickets could get merged quicker.

### What Did Not Work
* Jira ticket splitting: subtasks were confusing and added overhead.
* Not a lot of tickets completed this sprint (US4 and Docker setup were heavy).
* Daily standups are not super helpful in this bot format (people just typing "Not working" or brief updates).

### Action Items for Sprint 3
* Remove User Story subtasks in Jira? — Yes! Track at story level only.
* Check Jira / US dependencies strictly before starting tickets.
* Focus next sprint on US5, US6, US7, and US8.

---

# Sprint 3 (US5, US6, US7 Core Features)

## Sprint 3 Review
* **Date:** Friday, Nov 13, 2026
* **Attendees:** Tyler, Richard, Riley, Steph, Cameron
* **Goal:** Implement US5 (Manage Listings), US7 (Confirm Pickup), and finalize reservation management flows.

### Completed Work & Demos
* **User Stories Implemented & Passing in Docker:**
  * `SCRUM-18` (PR #40) — US7: Confirm Pickup
    * Vendors enter student's 6-character pickup code during the active pickup window.
    * Status updates to "picked up", displaying student name and portions to hand out.
    * Non-existent, wrong-vendor, cancelled, or already-used codes rejected with clear error alerts.
    * Active reservations on expired pickup windows automatically marked as "no-show".
  * `SCRUM-19` (PR #45) — US5: Manage Listings
    * "My Listings" dashboard displays active, ended, and cancelled listings with reserved/remaining counts.
    * Edit validations enforce US2 rules and prevent setting total portions below already reserved count.
    * Cancelling a listing removes it from student feed and cascades status "cancelled" to active reservations.
    * Vendor detail view lists students and portion counts for each reserved order.
  * `SCRUM-20` (PR #39) — US6: My Reservations
    * Student reservations page displays listing details, location, pickup windows, codes, and status badges.
    * Active reservations can be cancelled before pickup window ends, returning portions back to listing inventory.

---

## Sprint 3 Retrospective (Meeting 4)
* **Date:** Friday, Nov 13, 2026
* **Attendees:** Tyler, Richard, Riley, Steph, Cameron

### Previous Action Items Status (from Sprint 2 Retro)
* **Remove User Story subtasks in Jira:** Carried out. Tracking directly at the story level eliminated ticket overhead and kept PR titles clean.
* **Check dependencies:** Carried out. US7 waited on US4; US5 waited on US2/US4; zero dependency blockers.
* **Focus on remaining stories:** Carried out. US5, US6, and US7 fully completed and merged.

### What Worked
* Everything went really well this sprint.
* Reviews were solid and prompt, and lots of work got done quickly.
* Quick turnaround in Discord when review requests were posted.

### Action Items for Final Sprint
* Continue this momentum into the final sprint!
* Finish remaining optional bonus stories (US8 Filter Listings, US9 Impact Dashboard, US10 Rate a Pickup) and final tech debt.

---

# Sprint 4 (Optional Bonus Features US8, US9, US10 & Polish)

## Sprint 4 Review
* **Date:** Sunday, Nov 15, 2026
* **Attendees:** Tyler, Richard, Riley, Steph, Cameron
* **Goal:** Complete all 3 optional bonus stories (US8, US9, US10), resolve technical debt, populate realistic demo seed data, and verify full system in Docker Compose.

### Completed Work & Demos
* **User Stories Implemented & Passing in Docker:**
  * `SCRUM-21` (PR #50) — US8: Filter Listings (Bonus)
    * Dietary tag filters (vegetarian, vegan, gluten-free, halal, contains nuts) requiring all selected tags to match.
    * Campus location filter combined with dietary filters.
    * One-click "Clear filters" button immediately restores full available listings feed.
  * `SCRUM-22` (PR #49) — US9: Impact Dashboard (Bonus)
    * Vendor analytics dashboard with custom date range selection.
    * Metrics show total listings posted, portions posted, portions rescued, and no-show count.
    * No-show rate calculated and displayed as a percentage of reserved portions. Zero-data ranges default safely to 0 without errors.
  * `SCRUM-23` (PR #47) — US10: Rate a Pickup (Bonus)
    * Students give 1–5 star ratings and optional comments (up to 300 chars) on picked-up reservations.
    * Single-rating enforcement per reservation; uncollected or cancelled reservations cannot be rated.
    * Vendors see aggregate average rating and customer feedback comments on their listing pages.
* **Technical Debt, Seed Data & UX Polish:**
  * `SCRUM-48` (PR #48):
    * Standardized timezone normalization using UTC across all routes and database models.
    * Added vendor cancellation attribution ("Cancelled by Vendor" badge and struck-through codes on student view).
    * Automated Selenium database teardown to prevent test data pollution.
    * Populated 4 realistic campus food surplus listings in `seed.py` with active pickup windows and dietary tags for grading.
* All 10 user stories (7 required + 3 optional bonus) fully verified passing in Docker Compose.
