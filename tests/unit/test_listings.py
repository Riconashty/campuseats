import sys
from datetime import datetime, timedelta
from pathlib import Path
import unittest

# Ensure Python can find the campuseats package
src_path = str(Path(__file__).resolve().parent.parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from campuseats import create_app
from campuseats.config import TestingConfig
from campuseats.extensions import db
from campuseats.models.listing import DEFAULT_DIETARY_TAGS, DietaryTag, Listing
from campuseats.models.user import User


class ListingsTestCase(unittest.TestCase):
    # Set up test application and client with in-memory database
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()

    # Helper method to register and log in a user with a specified role
    def _create_and_login_user(self, name, email, password, role):
        self.client.post(
            "/register",
            data={
                "name": name,
                "email": email,
                "password": password,
                "role": role,
            },
        )
        self.client.post(
            "/login",
            data={
                "email": email,
                "password": password,
            },
        )

    # Verify Listing and DietaryTag models and their relationships
    def test_listing_and_dietary_tag_models(self):
        with self.app.app_context():
            vendor = User(
                name="Chef Luigi",
                email="luigi@example.invalid",
                password_hash="fakehash",
                role="vendor",
            )
            db.session.add(vendor)
            db.session.commit()

            start_time = datetime.now() + timedelta(hours=1)
            end_time = datetime.now() + timedelta(hours=3)

            listing = Listing(
                vendor_id=vendor.id,
                title="Pasta Marinara Trays",
                description="Delicious fresh pasta",
                total_portions=25,
                remaining_portions=25,
                pickup_location="Campus Dining Hall B",
                pickup_start=start_time,
                pickup_end=end_time,
            )

            veg_tag = DietaryTag(name="vegetarian")
            halal_tag = DietaryTag(name="halal")
            listing.tags.append(veg_tag)
            listing.tags.append(halal_tag)

            db.session.add(listing)
            db.session.commit()

            saved_listing = db.session.get(Listing, listing.id)
            self.assertIsNotNone(saved_listing)
            self.assertEqual(saved_listing.status, "active")
            self.assertEqual(saved_listing.remaining_portions, 25)
            self.assertEqual(saved_listing.vendor.name, "Chef Luigi")
            self.assertEqual(len(saved_listing.tags), 2)
            self.assertIn("Pasta Marinara Trays", repr(saved_listing))
            self.assertIn("vegetarian", repr(veg_tag))

            # Verify vendor listings relationship
            self.assertEqual(len(vendor.listings), 1)
            self.assertEqual(vendor.listings[0].title, "Pasta Marinara Trays")

            # Verify reverse relationship from tag to listings
            self.assertEqual(veg_tag.listings.count(), 1)

    # Verify anonymous users are denied access to new listing routes
    def test_anonymous_access_denied(self):
        get_res = self.client.get("/listings/new")
        self.assertEqual(get_res.status_code, 403)

        post_res = self.client.post("/listings/new", data={"title": "Unauthorized"})
        self.assertEqual(post_res.status_code, 403)

        vendor_listings_res = self.client.get("/vendor/listings")
        self.assertEqual(vendor_listings_res.status_code, 403)

    # Verify student users are denied access to new listing routes
    def test_student_access_denied(self):
        self._create_and_login_user(
            name="Alice Student",
            email="alice@example.invalid",
            password="Password123!",
            role="student",
        )

        get_res = self.client.get("/listings/new")
        self.assertEqual(get_res.status_code, 403)

        post_res = self.client.post("/listings/new", data={"title": "Unauthorized"})
        self.assertEqual(post_res.status_code, 403)

        vendor_listings_res = self.client.get("/vendor/listings")
        self.assertEqual(vendor_listings_res.status_code, 403)

    # Verify vendor can view the new listing form and vendor listings overview
    def test_vendor_can_view_listing_form_and_overview(self):
        self._create_and_login_user(
            name="Bob Vendor",
            email="bob@example.invalid",
            password="VendorPassword123!",
            role="vendor",
        )

        get_res = self.client.get("/listings/new")
        self.assertEqual(get_res.status_code, 200)
        self.assertIn(b"Post a Surplus Food Listing", get_res.data)
        for tag in DEFAULT_DIETARY_TAGS:
            self.assertIn(tag.encode(), get_res.data)

        overview_res = self.client.get("/vendor/listings")
        self.assertEqual(overview_res.status_code, 200)
        self.assertIn(b"My Surplus Food Listings", overview_res.data)

    # Verify valid listing submission creates listing and redirects
    def test_post_listing_success(self):
        self._create_and_login_user(
            name="Bob Vendor",
            email="bob@example.invalid",
            password="VendorPassword123!",
            role="vendor",
        )

        start_time = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
        end_time = (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M")

        response = self.client.post(
            "/listings/new",
            data={
                "title": "Fresh Fruit & Sandwiches",
                "description": "Leftover from afternoon seminar",
                "portions": "15",
                "pickup_location": "Student Union Room 204",
                "pickup_start": start_time,
                "pickup_end": end_time,
                "dietary_tags": ["vegetarian", "vegan"],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/vendor/listings")

        with self.app.app_context():
            listing = db.session.execute(
                db.select(Listing).filter_by(title="Fresh Fruit & Sandwiches")
            ).scalar_one_or_none()
            self.assertIsNotNone(listing)
            self.assertEqual(listing.total_portions, 15)
            self.assertEqual(listing.remaining_portions, 15)
            self.assertEqual(listing.pickup_location, "Student Union Room 204")
            self.assertEqual(listing.status, "active")
            tag_names = [t.name for t in listing.tags]
            self.assertIn("vegetarian", tag_names)
            self.assertIn("vegan", tag_names)

        # Check that overview page displays the created listing
        overview_res = self.client.get("/vendor/listings")
        self.assertIn(b"Fresh Fruit &amp; Sandwiches", overview_res.data)
        self.assertIn(b"15 / 15", overview_res.data)

    # Verify posting without description succeeds and stores empty description as None
    def test_post_listing_optional_description(self):
        self._create_and_login_user(
            name="Bob Vendor",
            email="bob@example.invalid",
            password="VendorPassword123!",
            role="vendor",
        )

        start_time = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
        end_time = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")

        response = self.client.post(
            "/listings/new",
            data={
                "title": "Pizza Slices",
                "description": "",
                "portions": "8",
                "pickup_location": "Engineering Lobby",
                "pickup_start": start_time,
                "pickup_end": end_time,
            },
        )

        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            listing = db.session.execute(
                db.select(Listing).filter_by(title="Pizza Slices")
            ).scalar_one_or_none()
            self.assertIsNotNone(listing)
            self.assertIsNone(listing.description)
            self.assertEqual(len(listing.tags), 0)

    # Verify missing required fields fail validation
    def test_post_listing_missing_required_fields(self):
        self._create_and_login_user(
            name="Bob Vendor",
            email="bob@example.invalid",
            password="VendorPassword123!",
            role="vendor",
        )

        # Missing title
        response = self.client.post(
            "/listings/new",
            data={
                "title": "",
                "portions": "10",
                "pickup_location": "Cafeteria",
                "pickup_start": "2026-11-01T12:00",
                "pickup_end": "2026-11-01T14:00",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Missing: Title", response.data)

        # Missing portions
        response = self.client.post(
            "/listings/new",
            data={
                "title": "Salad Bowls",
                "portions": "",
                "pickup_location": "Cafeteria",
                "pickup_start": "2026-11-01T12:00",
                "pickup_end": "2026-11-01T14:00",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Missing: Portions", response.data)

        # Missing pickup location
        response = self.client.post(
            "/listings/new",
            data={
                "title": "Salad Bowls",
                "portions": "5",
                "pickup_location": "",
                "pickup_start": "2026-11-01T12:00",
                "pickup_end": "2026-11-01T14:00",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Missing: Pickup Location", response.data)

    # Verify invalid portion values are rejected
    def test_post_listing_invalid_portions(self):
        self._create_and_login_user(
            name="Bob Vendor",
            email="bob@example.invalid",
            password="VendorPassword123!",
            role="vendor",
        )

        start_time = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
        end_time = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")

        # Portions below 1
        res_zero = self.client.post(
            "/listings/new",
            data={
                "title": "Soup",
                "portions": "0",
                "pickup_location": "Kitchen",
                "pickup_start": start_time,
                "pickup_end": end_time,
            },
        )
        self.assertEqual(res_zero.status_code, 200)
        self.assertIn(b"Portions must be an integer between 1 and 100", res_zero.data)

        # Portions above 100
        res_large = self.client.post(
            "/listings/new",
            data={
                "title": "Soup",
                "portions": "101",
                "pickup_location": "Kitchen",
                "pickup_start": start_time,
                "pickup_end": end_time,
            },
        )
        self.assertEqual(res_large.status_code, 200)
        self.assertIn(b"Portions must be an integer between 1 and 100", res_large.data)

        # Non-numeric portions
        res_nonnum = self.client.post(
            "/listings/new",
            data={
                "title": "Soup",
                "portions": "five",
                "pickup_location": "Kitchen",
                "pickup_start": start_time,
                "pickup_end": end_time,
            },
        )
        self.assertEqual(res_nonnum.status_code, 200)
        self.assertIn(b"Portions must be an integer between 1 and 100", res_nonnum.data)

    # Verify pickup end in the past is rejected
    def test_post_listing_pickup_end_in_past(self):
        self._create_and_login_user(
            name="Bob Vendor",
            email="bob@example.invalid",
            password="VendorPassword123!",
            role="vendor",
        )

        past_start = (datetime.now() - timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M")
        past_end = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")

        response = self.client.post(
            "/listings/new",
            data={
                "title": "Breakfast Tacos",
                "portions": "10",
                "pickup_location": "Cafe South",
                "pickup_start": past_start,
                "pickup_end": past_end,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Pickup end time cannot be in the past", response.data)

    # Verify pickup end before or equal to pickup start is rejected
    def test_post_listing_pickup_end_before_or_equal_to_start(self):
        self._create_and_login_user(
            name="Bob Vendor",
            email="bob@example.invalid",
            password="VendorPassword123!",
            role="vendor",
        )

        start_time = (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M")
        earlier_end = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")

        # Pickup end before start
        response_before = self.client.post(
            "/listings/new",
            data={
                "title": "Croissants",
                "portions": "10",
                "pickup_location": "Bakery",
                "pickup_start": start_time,
                "pickup_end": earlier_end,
            },
        )
        self.assertEqual(response_before.status_code, 200)
        self.assertIn(
            b"Pickup end time must be after pickup start time",
            response_before.data,
        )

        # Pickup end equal to start
        response_equal = self.client.post(
            "/listings/new",
            data={
                "title": "Croissants",
                "portions": "10",
                "pickup_location": "Bakery",
                "pickup_start": start_time,
                "pickup_end": start_time,
            },
        )
        self.assertEqual(response_equal.status_code, 200)
        self.assertIn(
            b"Pickup end time must be after pickup start time",
            response_equal.data,
        )

    # Verify malformed datetimes are rejected gracefully
    def test_post_listing_invalid_datetime_format(self):
        self._create_and_login_user(
            name="Bob Vendor",
            email="bob@example.invalid",
            password="VendorPassword123!",
            role="vendor",
        )

        response = self.client.post(
            "/listings/new",
            data={
                "title": "Muffins",
                "portions": "12",
                "pickup_location": "Bakery",
                "pickup_start": "not-a-datetime",
                "pickup_end": "also-invalid",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Please provide valid dates and times for the pickup window",
            response.data,
        )


if __name__ == "__main__":
    unittest.main()
