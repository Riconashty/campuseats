# CampusEats: Sprint Planning

---

## Backlog Scoring & Prioritization

| ID | Short name | User value | Estimate | Priority score | Rank |
| --- | --- | --- | --- | --- | --- |
| US1 | Register and log in | 3 | 4 | 0.75 | 1 |
| US2 | Post a listing | 3 | 2 | 1.50 | 2 |
| US3 | Browse listings | 3 | 1 | 3.00 | 3 |
| US4 | Reserve portions | 3 | 3 | 1.00 | 4 |
| US5 | Manage listings | 2 | 2 | 1.00 | 5 |
| US6 | My reservations | 2 | 2 | 1.00 | 6 |
| US7 | Confirm pickup | 3 | 2 | 1.50 | 7 |
| US8 | Filter listings | 2 | 1 | 2.00 | 8 |
| US9 | Impact dashboard | 1 | 1 | 1.00 | 9 |
| US10 | Rate a pickup | 1 | 3 | 0.33 | 10 |
| **Total** | | **23** | **21** | **1.09** | |

---

## Team Capacity & Release Plan

Justification: 5 team members with full course loads, dedicating about 5 hours a week each.

| Sprint | User stories (in order) | Planned | Remaining | Dependencies checked (Y/N) |
| --- | --- | --- | --- | --- |
| Sprint 1 | US1 (Register and log in) | 4 | 17 | Y |
| Sprint 2 | US2 (Post a listing), US3 (Browse listings), US4 (Reserve portions) | 6 | 11 | Y |
| Sprint 3 | US5 (Manage listings), US6 (My reservations), US7 (Confirm pickup) | 6 | 5 | Y |
| Sprint 4 | US8 (Filter listings), US9 (Impact dashboard), US10 (Rate a pickup) | 5 | 0 | Y |
| **Total** | US1 – US10 | 21 | — | — |

---

## Sprint 0: Planning

- **Date:** 10/19/26
- **Attendees:** Tyler, Riley, Cameron, Richard, Steph
- **Goal:** Project setup, backlog scoring, architecture, and UML diagrams.
- **Tasks:**
  - SCRUM-5: UML Class diagram
  - SCRUM-6: Sequence diagram
  - SCRUM-7: Backlog scoring
  - SCRUM-8: Sprint planning & roadmap
  - SCRUM-10: Local dev environment setup
  - SCRUM-11: GitHub repo & branch protections

---

## Sprint 1 Planning

- **Date:** 10/23/26
- **Attendees:** Tyler, Riley, Cameron, Richard, Steph
- **Goal:** Flask setup, database connection, CI script, and US1.
- **Tasks & Stories:**
  - SCRUM-12: Setup Flask
  - SCRUM-13: Setup PostgreSQL
  - SCRUM-31: Automated CI script
  - SCRUM-14: US1 - Register and log in
    - SCRUM-24: User model & registration
    - SCRUM-25: Login, logout, and role redirects

---

## Sprint 2 Planning

- **Date:** 10/27/26
- **Attendees:** Tyler, Riley, Cameron, Richard, Steph
- **Goal:** Core marketplace features (US2, US3, US4) and Docker Compose setup.
- **Tasks & Stories:**
  - SCRUM-15: US2 - Post a Listing
    - SCRUM-26: Listing & tag models
    - SCRUM-27: Post listing form & validation
  - SCRUM-16: US3 - Browse Listings
  - SCRUM-17: US4 - Reserve Portions
    - SCRUM-28: Reservation model & booking logic
    - SCRUM-29: Reservation modal & pickup code
  - Docker Compose & Selenium test

---

## Sprint 3 Planning

- **Date:** 11/03/26
- **Attendees:** Tyler, Riley, Cameron, Richard, Steph
- **Goal:** Listings management, student reservations page, and pickup confirmations (US5, US6, US7).
- **Tasks & Stories:**
  - SCRUM-19: US5 - Manage Listings
  - SCRUM-20: US6 - My Reservations
  - SCRUM-18: US7 - Confirm Pickup

---

## Sprint 4 Planning

- **Date:** 11/10/26
- **Attendees:** Tyler, Riley, Cameron, Richard, Steph
- **Goal:** Bonus features (US8, US9, US10), final manual testing, and submission polish.
- **Tasks & Stories:**
  - SCRUM-21: US8 - Filter Listings
  - SCRUM-22: US9 - Impact Dashboard
  - SCRUM-23: US10 - Rate a Pickup
