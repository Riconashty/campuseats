# CampusEats

CampusEats connects campus food vendors that have leftover food with students who want it, reducing food waste and hunger on campus.

---

## Quick Start

Each team designates one member as the **Scrum Master** before Sprint 1 begins and records that name in the README. The Scrum Master also writes code, but is additionally responsible for facilitating sprint planning, daily scrums, reviews and retrospectives, making sure meeting notes are recorded in the scrum folder on time. 

The Product Owner role is played by the instructor. The instructor has written the backlog and set the user value of each story; your team decides effort, priority within the rules below, and how the work is split.

```
Scrum Master: Riley Drenth
```

# Project Vision

**CampusEats** connects campus food vendors that have leftover food with students who want it, so less food is thrown away and fewer students go hungry.

Today, dining halls and campus cafés throw away trays of good food at closing time, while many students skip meals to save money. Vendors have no simple way to announce leftovers, and students hear about them too late or not at all. The campus sustainability office wants a web app where vendors post surplus food with a pickup window, students reserve portions, and vendors confirm pickups so the office can measure how much food was rescued.

# Product Backlog

The backlog has 10 user stories: US1 to US7 are required and US8 to US10 are optional. User value is set by the Product Owner: 3 = high, 2 = medium, 1 = low. "Depends on" means a story cannot start until the listed stories are finished (merged into dev and passing their acceptance criteria).

| ID | User story | User value | Depends on | Type |
| --- | --- | --- | --- | --- |
| US1 | As a new user, I want to register and log in as either a student or a vendor so that I can use the features for my role. | 3 | — | Required |
| US2 | As a vendor, I want to post a surplus food listing with portions and a pickup window so that students know what food is available and when. | 3 | US1 | Required |
| US3 | As a student, I want to browse the food listings that are currently available so that I can find food before it is thrown away. | 3 | US2 | Required |
| US4 | As a student, I want to reserve portions from a listing so that the food is held for me until I pick it up. | 3 | US1, US3 | Required |
| US5 | As a vendor, I want to edit or cancel my listings and see who reserved them so that the information students see stays accurate. | 2 | US2, US4 | Required |
| US6 | As a student, I want to see and cancel my reservations so that portions I no longer need are released to other students. | 2 | US4 | Required |
| US7 | As a vendor, I want to confirm a pickup by entering the student's pickup code so that food goes only to the student who reserved it. | 3 | US4 | Required |
| US8 | As a student, I want to filter listings by dietary tag and campus location so that I only see food I can eat and reach. | 2 | US3 | Optional |
| US9 | As a vendor, I want an impact dashboard showing portions rescued and no-shows so that I can report results to the sustainability office. | 1 | US7 | Optional |
| US10 | As a student, I want to rate a pickup after collecting my food so that vendors get feedback on quality and service. | 1 | US7 | Optional |

# Acceptance Criteria

A story is done only when every one of its acceptance criteria passes in the Docker Compose deployment. Use these criteria to write your Selenium test and your manual test cases.

## US1: Register and log in (Required)

1. Given I am on the registration page, when I enter a name, a unique email, a password of at least 8 characters, select "Student" or "Vendor", and click "Register", then my account is stored in PostgreSQL and I am redirected to the login page.
2. Given an account with that email already exists, when I submit the form, then no account is created and I see an error saying the email is already registered.
3. Given any required field is empty, when I submit the form, then no account is created and the empty field is identified.
4. Passwords are stored hashed, never in plain text.
5. Given I have an account, when I log in with the correct email and password, then I land on the home page for my role; with a wrong password, I see an error and stay logged out.

## US2: Post a surplus food listing (Required)

1. Given I am logged in as a vendor, when I enter a title, description, number of portions (1 to 100), pickup location, zero or more dietary tags (vegetarian, vegan, gluten-free, halal, contains nuts), and a pickup window start and end, and click "Post", then the listing is stored and linked to my vendor account.
2. Given the pickup window end is before its start, or the end is in the past, when I click "Post", then the listing is not saved and I see an error.
3. Given I am logged in as a student, when I try to open the new-listing page, then access is denied.

## US3: Browse available listings (Required)

1. Given I am logged in as a student, when I open the listings page, then I see every listing whose pickup window has not ended, that has at least one portion left, and that has not been cancelled.
2. Each listing shows its title, vendor name, pickup location, dietary tags, portions remaining, and pickup window.
3. Listings are sorted by pickup window end, soonest first.
4. Given no listings are available, then I see a message saying so instead of an empty page.

## US4: Reserve portions (Required)

1. Given a listing has portions remaining, when I choose 1 or 2 portions and click "Reserve", then a reservation is stored, the listing's remaining portions decrease by that amount, and I see a unique 6-character pickup code.
2. Given I request more portions than remain, then no reservation is created and I see an error.
3. Given I already hold an active reservation for that listing, when I try to reserve again, then I am told I already have a reservation.
4. Given two students reserve the last portion at the same moment, then only one reservation succeeds (remaining portions never go below zero).

## US5: Manage listings (Required)

1. Given I am logged in as a vendor, when I open "My Listings", then I see all my listings with their status (active, ended, cancelled) and portions reserved and remaining.
2. Given a listing has no reservations, when I edit its fields and save, then the changes are stored and validated with the same rules as US2.
3. Given a listing has reservations, when I edit it, then I cannot set the number of portions below the number already reserved.
4. When I cancel a listing, then it no longer appears to students and all its active reservations are marked cancelled.
5. When I open a listing, then I see the name and portions of every student who reserved it. Vendors cannot see or change other vendors' listings.

## US6: View and cancel my reservations (Required)

1. Given I am logged in as a student, when I open "My Reservations", then I see each reservation with listing title, vendor, location, pickup window, portions, pickup code, and status (active, picked up, cancelled, no-show).
2. Given a reservation is active and its pickup window has not ended, when I click "Cancel", then its status becomes cancelled and its portions are returned to the listing.
3. Given a reservation is not active, then no "Cancel" option is shown.

## US7: Confirm pickup (Required)

1. Given I am logged in as a vendor, when I enter a pickup code for an active reservation on one of my listings during its pickup window, then the reservation status becomes "picked up" and I see the student name and portions to hand out.
2. Given the code does not exist, belongs to another vendor's listing, or was already used or cancelled, then the pickup is rejected with a clear message.
3. Given a pickup window has ended, then every reservation on that listing that is still active is shown with status "no-show".

## US8: Filter listings (Optional)

1. Given I am on the listings page, when I select one or more dietary tags, then only listings that have all selected tags are shown.
2. When I select a campus location, then only listings at that location are shown; filters can be combined with dietary tags.
3. When I click "Clear filters", then all available listings are shown again.

## US9: Impact dashboard (Optional)

1. Given I am logged in as a vendor, when I open the dashboard and choose a date range, then I see the number of listings posted, portions posted, portions picked up, and no-show count for my listings in that range.
2. The no-show rate is shown as a percentage of reserved portions.
3. Given there is no data in the range, then all values show 0 and no error occurs.

## US10: Rate a pickup (Optional)

1. Given a reservation of mine has status "picked up", when I give it 1 to 5 stars and an optional comment of up to 300 characters and click "Submit", then the rating is stored and linked to that reservation.
2. I can rate each picked-up reservation only once; reservations in any other status cannot be rated.
3. Vendors see the average rating and the comments for each of their listings.

# Scoring and Prioritizing the Backlog

Before Sprint 1 starts, your team estimates every story and ranks the backlog using the same method as Activity 17. Record the result in the table below. 

| ID | Short name | User value | Story points | Priority score | Rank |
| --- | --- | --- | --- | --- | --- |
| US1 | Register and log in | 3 |  |  |  |
| US2 | Post a listing | 3 |  |  |  |
| US3 | Browse listings | 3 |  |  |  |
| US4 | Reserve portions | 3 |  |  |  |
| US5 | Manage listings | 2 |  |  |  |
| US6 | My reservations | 2 |  |  |  |
| US7 | Confirm pickup | 3 |  |  |  |
| US8 | Filter listings | 2 |  |  |  |
| US9 | Impact dashboard | 1 |  |  |  |
| US10 | Rate a pickup | 1 |  |  |  |
| **Total** |  |  |  |  |  |

Priority Score Formula: 

![pics/pic1.png](pics/pic1.png)

# Sprint Planning

The project runs as a planning phase (Sprint 0) followed by three one-week sprints, and every sprint ends with a tagged release (v1, v2, and v3).

Before writing any code, split the backlog across the three sprints and record it below. Follow these rules:

* Capacity: set your team's capacity in story points per sprint and justify it in one or two sentences (team size, hours available, course load). No sprint may exceed it.
* Dependencies: a story can be in the same sprint as a story it depends on only if the plan shows the dependency finishing first; otherwise it goes in a later sprint.
* Required first: all seven required stories (US1 to US7) must be planned for Sprints 1 to 3. Optional stories (US8 to US10) are planned only in space left over.
* Priority: within those limits, higher-ranked stories go earlier.
* Planned burndown: list the story points remaining at the start and after each planned sprint.

### 1. Clone the Repository
```bash
git clone git@github.com:Riconashty/campuseats.git
cd campuseats
```

### 2. Create and Activate Virtual Environment
```bash
python3 -m venv .venv
```

- **macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```
- **Windows (Command Prompt / PowerShell):**
  ```cmd
  .venv\Scripts\activate
  ```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
pip install -e .
```

### 4. Create Environment Configuration
```bash
cp .env.example .env
```

### 5. Run the Application
```bash
python3 run.py
```