# Manual test record

Every acceptance criterion of every implemented story except US4 is tested by hand here.
US4 (Reserve portions) is the team's automated story: all four of its criteria are covered
by the Selenium black box test in `tests/integration/test_us4_selenium.py`.

A criterion is only marked **passed** after a team member has carried out its steps (see
[How to run each check](#how-to-run-each-check)) against the Docker Compose deployment.
Failures are recorded as **failed**, with what happened in Notes, and get a new row when
they are re-tested after a fix.

## Test run

| | |
| --- | --- |
| Build tested (commit or tag) | |
| Started with | `docker compose down -v` then `docker compose up --build` |
| Address | http://localhost:5000 |
| Browser | |

| User story | Acceptance criterion | Tester | Date | Result | Notes |
| --- | --- | --- | --- | --- | --- |
| US1 | 1: registering stores the account and redirects to the login page |Richard Hall | 2026-10-29 | verified | |
| US1 | 2: duplicate email rejected |Richard Hall |2026-10-29 |verified | |
| US1 | 3: empty required field is identified and no account is created |Richard Hall | 2026-10-29 | verified | |
| US1 | 4: password is stored hashed, not in plain text |Richard Hall | 2026-10-29 | verified | |
| US1 | 5: correct login lands on the role's home page; wrong password shows an error and stays logged out |Richard Hall | 2026-10-29 | verified | |
| US2 | 1: vendor posts a listing and it is stored under their account |Stephanie Rivera-Martinez |2026-11-01  |verified | |
| US2 | 2: pickup end before start, or end in the past, is rejected |Stephanie Rivera-Martinez |2026-11-01  |verified | |
| US2 | 3: student is denied access to the new-listing page |Stephanie Rivera-Martinez |2026-11-01  |verified | |
| US3 | 1: feed shows every listing that has not ended, has a portion left, and is not cancelled |Tyler Black |2026-11-03 |Verified | |
| US3 | 2: each listing shows title, vendor name, location, dietary tags, portions remaining, and pickup window |Tyler Black |2026-11-03 |Verified | |
| US3 | 3: listings are sorted by pickup window end, soonest first |Tyler Black |2026-11-03 |Verified | |
| US3 | 4: a message is shown when no listings are available |Tyler Black |2026-11-03 |Verified | |
| US5 | 1: My Listings shows every listing with its status and portions reserved and remaining |Tyler Black |2026-11-12 |Verified | |
| US5 | 2: editing a listing with no reservations saves the changes, with the US2 rules applied |Tyler Black |2026-11-12 |Verified | |
| US5 | 3: portions cannot be set below the number already reserved |Tyler Black |2026-11-12 |Verified | |
| US5 | 4: cancelling a listing hides it from students and cancels its active reservations |Tyler Black |2026-11-12 |Verified | |
| US5 | 5: listing detail shows each student's name and portions; other vendors' listings cannot be seen or changed |Tyler Black |2026-11-12 |Verified | |
| US6 | 1: My Reservations shows title, vendor, location, pickup window, portions, pickup code, and status |Tyler Black |2026-11-08 |Verified | |
| US6 | 2: cancelling an active reservation marks it cancelled and returns its portions |Tyler Black |2026-11-08 |Verified | |
| US6 | 3: no Cancel option for a reservation that is not active |Tyler Black |2026-11-08 |Verified | |
| US7 | 1: a valid code during the pickup window marks the reservation picked up and shows the student name and portions |
Cameron Greeson |2026-11-12 | verified| |
| US7 | 2: a code that does not exist, belongs to another vendor, or was already used or cancelled is rejected with a clear message |
Cameron Greeson |2026-11-12 | verified| |
| US7 | 3: after the pickup window ends, reservations still active are shown as no-show |
Cameron Greeson |2026-11-12 | verified| |
| US8 | 1: selecting dietary tags shows only listings that have all selected tags |
Cameron Greeson |2026-11-12 | verified| |
| US8 | 2: selecting a location shows only listings there, and combines with dietary tags |Tyler Black|2026-11-14|verified| |
| US8 | 3: Clear filters shows all available listings again |Tyler Black|2026-11-14|verified| |
| US9 | 1: dashboard shows listings posted, portions posted, portions picked up, and no-show count for a date range |Tyler Black|2026-11-14|verified| |
| US9 | 2: no-show rate is shown as a percentage of reserved portions |Tyler Black|2026-11-14|verified| |
| US9 | 3: a range with no data shows 0 everywhere and no error |Tyler Black|2026-11-14|verified| |
| US10 | 1: a picked-up reservation can be rated 1 to 5 stars with an optional comment of up to 300 characters |Richard Hall |2026-11-14|verified| |
| US10 | 2: each picked-up reservation can be rated only once; other statuses cannot be rated |Richard Hall |2026-11-14|verified| |
| US10 | 3: vendor sees the average rating and the comments for each listing |Richard Hall |2026-11-14|verified| |

## How to run each check

Start from an empty database so the results do not depend on earlier runs:

```bash
docker compose down -v
docker compose up --build
```

Then open http://localhost:5000. The seed accounts are created on first start, together
with four sample listings owned by the vendor:

| Role | Email | Password |
| --- | --- | --- |
| Vendor | `vendor@campuseats.edu` | `Vendor123!` |
| Student | `student@campuseats.edu` | `Student123!` |

Several checks need a second vendor or a second student. Register them on the Register
page as you go. Using one normal browser window and one private window lets you stay
logged in as a vendor and a student at the same time.

### US1: Register and log in

1. On **Register**, enter a name, an email not used before, a password of 8 or more
   characters, choose Student, and submit. Expected: you are on the login page with
   "Account created successfully!". Repeat choosing Vendor.
2. Register again with the same email as step 1. Expected: you stay on the registration
   page with "An account with that email already exists." Logging in with that email and
   the second password fails, so no second account was made.
3. The form will not submit with an empty field in a normal browser, and the browser
   points at the empty field. To also check the server's own message, open the developer
   console on the Register page, run `document.querySelector('form').noValidate = true`,
   leave one field empty, and submit. Expected: "Missing: Name." (or Email, Password,
   Role), and logging in with that email fails. Repeat once per field.
4. With the app running, in a second terminal run:

   ```bash
   docker compose exec db psql -U campuseats -d campuseats -c "SELECT email, password_hash FROM users;"
   ```

   Expected: every `password_hash` starts with `scrypt:` and none contains the password
   you typed.
5. Log in as the student from step 1. Expected: address ends in `/listings`. Log out, log
   in as the vendor. Expected: address ends in `/vendor/listings`. Log out, enter a real
   email with a wrong password. Expected: "Invalid email or password." and the
   navigation bar still shows Login.

### US2: Post a surplus food listing

1. As the vendor, open **Post Listing**. Enter a title, description, 10 portions, a
   location, tick two dietary tags, set a pickup window that ends in the future, and
   submit. Expected: "Listing posted successfully!" and the listing appears on **My
   Listings** with those values. Post another with no tags ticked; it is also accepted.
   Try 0 and 101 portions; both are rejected.
2. Submit once with the end time earlier than the start time, and once with both times
   yesterday. Expected: an error each time and no new listing on My Listings.
3. Log in as the student and go to http://localhost:5000/listings/new. Expected: a
   403 Forbidden page.

### US3: Browse available listings

1. As the vendor, make sure you have: one normal listing, one cancelled listing, one
   listing whose window has ended (US7 step 3 shows how to make one), and one listing
   with every portion reserved (post it with 1 portion and reserve that portion as a
   student). As the student, open **Browse Listings**. Expected: the normal listing and
   the seed listings are shown, and the other three are not.
2. Compare one card with the vendor's My Listings. Expected: the card shows the title,
   vendor name, location, dietary tags, portions left, and pickup window.
3. Read the pickup end times from top to bottom. Expected: soonest first.
4. Do this one last, because it cancels everything. As the vendor, cancel every active
   listing. As the student, reload the feed. Expected: "No Food Listings Available".

### US5: Manage listings

1. As the vendor, open **My Listings** with at least one active, one ended, and one
   cancelled listing, one of which has a reservation. Expected: all are listed with the
   right status and with Reserved and Remaining adding up to Total.
2. Edit a listing nobody has reserved: change the title, portions, location, and tags,
   and save. Expected: the new values show on My Listings. Edit again with the end time
   before the start time. Expected: an error and no change.
3. As a student, reserve 2 portions of a listing. As the vendor, edit that listing and
   set portions to 1. Expected: "Portions cannot be reduced below the 2 already
   reserved." and no change.
4. With that reservation still active, cancel the listing. Expected: the listing is gone
   from the student's feed, and the student's **My Reservations** shows the reservation
   as "Cancelled by Vendor".
5. Open a listing with reservations from My Listings. Expected: each student's name and
   portions are listed. Note the number at the end of the address, log in as a second
   vendor, and open `/vendor/listings/<that number>` and
   `/vendor/listings/<that number>/edit`. Expected: 403 Forbidden for both.

### US6: View and cancel my reservations

1. As the student, reserve from two listings and open **My Reservations**. Expected:
   each row shows the listing title, vendor, location, pickup window, portions, pickup
   code, and status.
2. Note a listing's "left" count on the feed, then cancel your reservation for it.
   Expected: the status becomes cancelled and the count on the feed goes back up by the
   portions you held.
3. Look at rows that are cancelled, picked up, or no-show. Expected: none has a Cancel
   button; only active rows do.

### US7: Confirm pickup

1. As the vendor, post a listing whose pickup window has already started (start time a
   few minutes ago, end time later today). As the student, reserve 2 portions and copy
   the code. As the vendor, open **Confirm Pickup** and enter it. Expected: "Pickup
   Confirmed!" with the student's name and 2 portions, and the student's My Reservations
   shows picked up.
2. On Confirm Pickup, enter in turn: `ZZZZZZ`; the code from step 1 again; the code of a
   reservation the student cancelled; and, logged in as a second vendor, a valid code for
   the first vendor's listing. Expected: each is refused with a message and nothing
   changes.
3. As the vendor, post a listing with a start time a few minutes ago and an end time
   3 minutes from now. As the student, reserve it. Do not enter the code. Wait until the
   end time has passed. Expected, without entering any code: the student's My
   Reservations shows **no-show**, the vendor's listing detail shows **No-show**, and
   the Impact Dashboard counts 1 no-show reservation.

### US8: Filter listings

1. As the student on Browse Listings, tick Vegan and apply. Expected: only listings
   tagged vegan. Tick Vegan and Halal. Expected: only listings that have both.
2. Choose a location. Expected: only listings at that location. Add a dietary tag.
   Expected: only listings matching both the location and the tag.
3. Click **Clear filters**. Expected: every available listing is shown again.

### US9: Impact dashboard

1. After the US7 checks, open **Impact Dashboard** as the vendor and set both dates to
   today. Expected: listings posted, portions posted, portions picked up, and no-show
   reservations match what you created today. Count them on My Listings to compare.
2. Work out no-show portions divided by reserved portions (picked up, no-show, and still
   active; cancelled ones do not count). Expected: the No-Show Rate shows that
   percentage.
3. Set both dates to a day last year. Expected: every card shows 0 and the page loads
   normally.

### US10: Rate a pickup

1. As the student, on My Reservations click **Rate Pickup** on the reservation picked up
   in US7 step 1. Give 4 stars and a short comment, and submit. Expected: "Thank you for
   your rating!" and the row shows "Rated: 4". On another picked-up reservation, submit
   with no comment; it is accepted. The comment box does not accept more than 300
   characters.
2. Expected: the rated row no longer offers Rate Pickup, and active, cancelled, and
   no-show rows never offer it. Opening `/student/reservations/<id>/rate` for the rated
   reservation shows "You have already rated this reservation."
3. As the vendor, open My Listings. Expected: the listing shows the average of its
   ratings and the comments under "review comments".
