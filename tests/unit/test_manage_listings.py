import unittest
from datetime import datetime, timedelta

from campuseats import create_app
from campuseats.config import TestingConfig
from campuseats.extensions import db
from campuseats.models.listing import DietaryTag, Listing
from campuseats.models.reservation import Reservation
from campuseats.models.user import User

FMT = "%Y-%m-%dT%H:%M"


class ManageListingsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        # The logged-in vendor is registered through the app so the session is real
        self.client.post(
            "/register",
            data={
                "name": "Owner",
                "email": "o@t.edu",
                "password": "Password123!",
                "role": "vendor",
            },
        )
        with self.app.app_context():
            self.owner_id = db.session.execute(
                db.select(User.id).filter_by(email="o@t.edu")
            ).scalar_one()
            other = User(name="Other Vendor", email="x@t.edu", password_hash="x", role="vendor")
            alice = User(name="Alice Adams", email="alice@t.edu", password_hash="x", role="student")
            bob = User(name="Bob Brown", email="bob@t.edu", password_hash="x", role="student")
            db.session.add_all([other, alice, bob])
            db.session.commit()
            self.other_id, self.alice_id, self.bob_id = other.id, alice.id, bob.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    # ---- helpers ----

    def login_owner(self):
        self.client.post("/login", data={"email": "o@t.edu", "password": "Password123!"})

    def login_student(self):
        self.client.post("/logout")
        self.client.post(
            "/register",
            data={"name": "Sam", "email": "s@t.edu", "password": "Password123!", "role": "student"},
        )
        self.client.post("/login", data={"email": "s@t.edu", "password": "Password123!"})

    def make_listing(
        self, vendor_id=None, title="Bagels", total=10, hours_until_end=2, status="active", tags=()
    ):
        now = datetime.now()
        with self.app.app_context():
            listing = Listing(
                vendor_id=vendor_id or self.owner_id,
                title=title,
                description="Fresh",
                total_portions=total,
                remaining_portions=total,
                pickup_location="Student Union",
                pickup_start=now - timedelta(hours=1),
                pickup_end=now + timedelta(hours=hours_until_end),
                status=status,
            )
            for name in tags:
                listing.tags.append(DietaryTag(name=name))
            db.session.add(listing)
            db.session.commit()
            return listing.id

    def reserve(self, listing_id, student_id, code, portions=1, status="active"):
        with self.app.app_context():
            listing = db.session.get(Listing, listing_id)
            if status != "cancelled":
                listing.remaining_portions -= portions
            db.session.add(
                Reservation(
                    student_id=student_id,
                    listing_id=listing_id,
                    portions_reserved=portions,
                    pickup_code=code,
                    status=status,
                )
            )
            db.session.commit()

    def listing_state(self, listing_id):
        with self.app.app_context():
            listing = db.session.get(Listing, listing_id)
            return {
                "title": listing.title,
                "status": listing.status,
                "total": listing.total_portions,
                "remaining": listing.remaining_portions,
                "tags": sorted(t.name for t in listing.tags),
                "reservations": sorted((r.pickup_code, r.status) for r in listing.reservations),
            }

    def form(self, **overrides):
        now = datetime.now()
        data = {
            "title": "Bagels (updated)",
            "description": "Now with cream cheese",
            "portions": "10",
            "pickup_location": "Library Cafe",
            "pickup_start": (now + timedelta(hours=1)).strftime(FMT),
            "pickup_end": (now + timedelta(hours=4)).strftime(FMT),
            "dietary_tags": ["vegan"],
        }
        data.update(overrides)
        return data

        # ---- AC1: My Listings dashboard ----

    def test_dashboard_shows_only_own_listings_with_status_and_counts(self):
        active = self.make_listing(title="Active Meal", total=10)
        self.make_listing(title="Ended Meal", hours_until_end=-1)
        self.make_listing(title="Cancelled Meal", status="cancelled")
        self.make_listing(vendor_id=self.other_id, title="Not Mine")
        self.reserve(active, self.alice_id, "AAAAAA", portions=2)
        self.reserve(active, self.bob_id, "BBBBBB", portions=1)
        self.login_owner()

        response = self.client.get("/vendor/listings")
        body = response.data.decode()
        self.assertEqual(response.status_code, 200)
        for text in ("Active Meal", "Ended Meal", "Cancelled Meal", "Active", "Ended", "Cancelled"):
            self.assertIn(text, body)
        self.assertNotIn("Not Mine", body)
        self.assertIn('<td class="portions-total">10</td>', body)
        self.assertIn('<td class="portions-reserved">3</td>', body)
        self.assertIn('<td class="portions-remaining">&mdash;</td>', body)

    def test_dashboard_hides_edit_and_cancel_for_inactive_listings(self):
        active = self.make_listing(title="Active Meal")
        ended = self.make_listing(title="Ended Meal", hours_until_end=-1)
        cancelled = self.make_listing(title="Cancelled Meal", status="cancelled")
        self.login_owner()
        body = self.client.get("/vendor/listings").data.decode()
        self.assertIn(f"/vendor/listings/{active}/edit", body)
        self.assertIn(f"/vendor/listings/{active}/cancel", body)
        for lid in (ended, cancelled):
            self.assertNotIn(f"/vendor/listings/{lid}/edit", body)
            self.assertNotIn(f"/vendor/listings/{lid}/cancel", body)

    # ---- AC2: detail view ----

    def test_detail_lists_students_with_name_email_and_portions(self):
        lid = self.make_listing()
        self.reserve(lid, self.alice_id, "AAAAAA", portions=2)
        self.reserve(lid, self.bob_id, "BBBBBB", portions=1)
        self.login_owner()
        body = self.client.get(f"/vendor/listings/{lid}").data.decode()
        for text in ("Alice Adams", "alice@t.edu", "Bob Brown", "bob@t.edu"):
            self.assertIn(text, body)

    def test_detail_empty_state(self):
        lid = self.make_listing()
        self.login_owner()
        response = self.client.get(f"/vendor/listings/{lid}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No students have reserved", response.data)

    # ---- AC3: edit ----

    def test_edit_form_is_prefilled(self):
        lid = self.make_listing(title="Prefilled Meal", tags=("halal",))
        self.login_owner()
        body = self.client.get(f"/vendor/listings/{lid}/edit").data.decode()
        self.assertIn('value="Prefilled Meal"', body)
        self.assertIn('value="Student Union"', body)
        self.assertIn('value="10"', body)
        self.assertRegex(body, r'name="pickup_end"\s+value="\d{4}-\d{2}-\d{2}T\d{2}:\d{2}"')
        self.assertRegex(body, r'value="halal"\s+id="tag-\d"\s+checked')

    def test_edit_saves_all_fields(self):
        lid = self.make_listing(tags=("halal",))
        self.login_owner()
        data = self.form(portions="12", dietary_tags=["halal", "vegan"])
        response = self.client.post(f"/vendor/listings/{lid}/edit", data=data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/vendor/listings")
        state = self.listing_state(lid)
        self.assertEqual(state["title"], "Bagels (updated)")
        self.assertEqual((state["total"], state["remaining"]), (12, 12))
        # halal already existed in the database; vegan is brand new. Both must be attached.
        self.assertEqual(state["tags"], ["halal", "vegan"])

    def test_edit_applies_us2_validation(self):
        lid = self.make_listing()
        self.login_owner()
        now = datetime.now()
        past = (now - timedelta(hours=2)).strftime(FMT)
        cases = [
            (self.form(title=""), b"Missing: Title"),
            (self.form(portions="0"), b"Portions must be an integer between 1 and 100"),
            (self.form(portions="101"), b"Portions must be an integer between 1 and 100"),
            (self.form(pickup_end="nope"), b"Please provide valid dates and times"),
            (
                self.form(pickup_start=(now - timedelta(hours=3)).strftime(FMT), pickup_end=past),
                b"Pickup end time cannot be in the past",
            ),
            (
                self.form(pickup_end=(now + timedelta(minutes=30)).strftime(FMT)),
                b"Pickup end time must be after pickup start time",
            ),
        ]
        for data, message in cases:
            response = self.client.post(f"/vendor/listings/{lid}/edit", data=data)
            self.assertEqual(response.status_code, 200)
            self.assertIn(message, response.data)
        self.assertEqual(self.listing_state(lid)["title"], "Bagels")

    # ---- AC4: portion reduction guard ----

    def test_cannot_reduce_portions_below_reserved(self):
        lid = self.make_listing(total=10)
        self.reserve(lid, self.alice_id, "AAAAAA", portions=2)
        self.reserve(lid, self.bob_id, "BBBBBB", portions=1)
        self.login_owner()
        response = self.client.post(f"/vendor/listings/{lid}/edit", data=self.form(portions="2"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"cannot be reduced below the 3 already reserved", response.data)
        state = self.listing_state(lid)
        self.assertEqual((state["total"], state["remaining"]), (10, 7))

    def test_changing_total_recalculates_remaining(self):
        lid = self.make_listing(total=10)
        self.reserve(lid, self.alice_id, "AAAAAA", portions=2)
        self.reserve(lid, self.bob_id, "BBBBBB", portions=1)
        self.login_owner()
        self.client.post(f"/vendor/listings/{lid}/edit", data=self.form(portions="3"))
        state = self.listing_state(lid)
        self.assertEqual((state["total"], state["remaining"]), (3, 0))
        self.client.post(f"/vendor/listings/{lid}/edit", data=self.form(portions="20"))
        state = self.listing_state(lid)
        self.assertEqual((state["total"], state["remaining"]), (20, 17))

    # ---- AC5 + AC6: cancel and cascade ----

    def test_cancel_marks_listing_and_only_active_reservations_cancelled(self):
        lid = self.make_listing(total=10)
        self.reserve(lid, self.alice_id, "AAAAAA", portions=2)
        self.reserve(lid, self.bob_id, "BBBBBB", portions=1, status="picked up")
        self.login_owner()
        response = self.client.post(f"/vendor/listings/{lid}/cancel")
        self.assertEqual(response.status_code, 302)
        state = self.listing_state(lid)
        self.assertEqual(state["status"], "cancelled")
        self.assertEqual(state["reservations"], [("AAAAAA", "cancelled"), ("BBBBBB", "picked up")])
        self.assertEqual(state["remaining"], 9)
        with self.app.app_context():
            res_alice = db.session.execute(
                db.select(Reservation).filter_by(pickup_code="AAAAAA")
            ).scalar_one()
            self.assertEqual(res_alice.cancellation_reason, "Cancelled by vendor")

    def test_cancelled_listing_disappears_from_student_feed(self):
        lid = self.make_listing(title="Soon Gone")
        self.login_owner()
        self.client.post(f"/vendor/listings/{lid}/cancel")
        self.login_student()
        self.assertNotIn(b"Soon Gone", self.client.get("/listings").data)
        self.client.post(f"/listings/{lid}/reserve", data={"portions": "1"})
        self.assertEqual(self.listing_state(lid)["reservations"], [])

    def test_cancel_requires_post_and_is_idempotent(self):
        lid = self.make_listing(total=10)
        self.reserve(lid, self.alice_id, "AAAAAA", portions=2)
        self.login_owner()
        self.assertEqual(self.client.get(f"/vendor/listings/{lid}/cancel").status_code, 405)
        self.client.post(f"/vendor/listings/{lid}/cancel")
        response = self.client.post(f"/vendor/listings/{lid}/cancel", follow_redirects=True)
        self.assertIn(b"can no longer be cancelled", response.data)
        self.assertEqual(self.listing_state(lid)["remaining"], 10)

    def test_inactive_listings_cannot_be_edited(self):
        ended = self.make_listing(hours_until_end=-1)
        cancelled = self.make_listing(status="cancelled")
        self.login_owner()
        for lid in (ended, cancelled):
            response = self.client.post(f"/vendor/listings/{lid}/edit", data=self.form())
            self.assertEqual(response.status_code, 302)
            self.assertEqual(self.listing_state(lid)["title"], "Bagels")

    # ---- AC7: isolation ----

    def test_other_vendors_listing_returns_403_everywhere(self):
        lid = self.make_listing(vendor_id=self.other_id, title="Not Mine")
        self.reserve(lid, self.alice_id, "AAAAAA")
        self.login_owner()
        self.assertEqual(self.client.get(f"/vendor/listings/{lid}").status_code, 403)
        self.assertEqual(self.client.get(f"/vendor/listings/{lid}/edit").status_code, 403)
        self.assertEqual(
            self.client.post(f"/vendor/listings/{lid}/edit", data=self.form()).status_code, 403
        )
        self.assertEqual(self.client.post(f"/vendor/listings/{lid}/cancel").status_code, 403)
        state = self.listing_state(lid)
        self.assertEqual((state["title"], state["status"]), ("Not Mine", "active"))
        self.assertEqual(state["reservations"], [("AAAAAA", "active")])

    def test_unknown_listing_returns_404(self):
        self.login_owner()
        self.assertEqual(self.client.get("/vendor/listings/9999").status_code, 404)
        self.assertEqual(self.client.get("/vendor/listings/9999/edit").status_code, 404)
        self.assertEqual(self.client.post("/vendor/listings/9999/cancel").status_code, 404)

    def test_students_and_anonymous_users_get_403(self):
        lid = self.make_listing()
        urls = [f"/vendor/listings/{lid}", f"/vendor/listings/{lid}/edit"]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(f"/vendor/listings/{lid}/cancel").status_code, 403)
        self.login_student()
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(f"/vendor/listings/{lid}/cancel").status_code, 403)
        self.assertEqual(self.listing_state(lid)["status"], "active")
