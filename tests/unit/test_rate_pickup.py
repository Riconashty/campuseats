import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from sqlalchemy.exc import IntegrityError

# Ensure Python can resolve the campuseats package
src_path = str(Path(__file__).resolve().parent.parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from campuseats import create_app
from campuseats.config import TestingConfig
from campuseats.extensions import db
from campuseats.models.listing import Listing
from campuseats.models.rating import Rating
from campuseats.models.reservation import Reservation
from campuseats.models.user import User
from campuseats.routes import role_guards
from campuseats.routes import student as student_routes


class RatePickupTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            vendor = User(
                name="Chef Vendor",
                email="vendor@example.invalid",
                password_hash="fakehash",
                role="vendor",
            )
            other_vendor = User(
                name="Other Vendor",
                email="othervendor@example.invalid",
                password_hash="fakehash",
                role="vendor",
            )
            alice = User(
                name="Alice Student",
                email="alice@example.invalid",
                password_hash="fakehash",
                role="student",
            )
            bob = User(
                name="Bob Student",
                email="bob@example.invalid",
                password_hash="fakehash",
                role="student",
            )
            db.session.add_all([vendor, other_vendor, alice, bob])
            db.session.commit()
            self.vendor_id = vendor.id
            self.other_vendor_id = other_vendor.id
            self.alice_id = alice.id
            self.bob_id = bob.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def login_as(self, user_id, role="student"):
        fake_user = SimpleNamespace(id=user_id, is_authenticated=True, role=role)
        for module in (role_guards, student_routes):
            patcher = patch.object(module, "current_user", fake_user)
            patcher.start()
            self.addCleanup(patcher.stop)

    def create_reservation(
        self,
        student_id,
        status="picked up",
        vendor_id=None,
        code="RAT001",
        title="Tasty Lunch",
    ):
        target_vendor_id = vendor_id or self.vendor_id
        now = datetime.now()
        with self.app.app_context():
            listing = Listing(
                vendor_id=target_vendor_id,
                title=title,
                total_portions=10,
                remaining_portions=5,
                pickup_location="Campus Center",
                pickup_start=now - timedelta(hours=2),
                pickup_end=now + timedelta(hours=2),
                status="active",
            )
            db.session.add(listing)
            db.session.flush()

            reservation = Reservation(
                student_id=student_id,
                listing_id=listing.id,
                portions_reserved=1,
                pickup_code=code,
                status=status,
            )
            db.session.add(reservation)
            db.session.commit()
            return reservation.id, listing.id

    # Model and Relationship Tests

    def test_rating_model_creation_and_attributes(self):
        res_id, _ = self.create_reservation(self.alice_id, code="MDL001")
        with self.app.app_context():
            rating = Rating(
                reservation_id=res_id,
                stars=5,
                comment="Outstanding fresh food and smooth pickup experience!",
            )
            db.session.add(rating)
            db.session.commit()

            fetched = db.session.get(Rating, rating.id)
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched.reservation_id, res_id)
            self.assertEqual(fetched.stars, 5)
            self.assertEqual(
                fetched.comment,
                "Outstanding fresh food and smooth pickup experience!",
            )
            self.assertIsNotNone(fetched.created_at)
            self.assertEqual(fetched.reservation.id, res_id)
            self.assertIn("5 stars", repr(fetched))

    def test_rating_stars_check_constraint(self):
        res_id, _ = self.create_reservation(self.alice_id, code="CST001")
        with self.app.app_context():
            rating_low = Rating(reservation_id=res_id, stars=0)
            db.session.add(rating_low)
            with self.assertRaises(IntegrityError):
                db.session.commit()
            db.session.rollback()

            rating_high = Rating(reservation_id=res_id, stars=6)
            db.session.add(rating_high)
            with self.assertRaises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_rating_unique_reservation_constraint(self):
        res_id, _ = self.create_reservation(self.alice_id, code="UNQ001")
        with self.app.app_context():
            first_rating = Rating(reservation_id=res_id, stars=4, comment="First rating")
            db.session.add(first_rating)
            db.session.commit()

            second_rating = Rating(reservation_id=res_id, stars=5, comment="Duplicate attempt")
            db.session.add(second_rating)
            with self.assertRaises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_rating_cascade_delete(self):
        res_id, _ = self.create_reservation(self.alice_id, code="CAS001")
        with self.app.app_context():
            rating = Rating(reservation_id=res_id, stars=4, comment="Will be deleted")
            db.session.add(rating)
            db.session.commit()
            rating_id = rating.id

            target_reservation = db.session.get(Reservation, res_id)
            db.session.delete(target_reservation)
            db.session.commit()

            self.assertIsNone(db.session.get(Rating, rating_id))

    def test_listing_ratings_and_average_properties(self):
        res1, listing_id = self.create_reservation(self.alice_id, code="AVG001")
        now = datetime.now()
        with self.app.app_context():
            listing = db.session.get(Listing, listing_id)
            self.assertIsNone(listing.average_rating)
            self.assertEqual(listing.ratings, [])
            self.assertEqual(listing.reviews_with_comments, [])

            res2 = Reservation(
                student_id=self.bob_id,
                listing_id=listing_id,
                portions_reserved=2,
                pickup_code="AVG002",
                status="picked up",
                created_at=now,
            )
            db.session.add(res2)
            db.session.commit()

            rating1 = Rating(reservation_id=res1, stars=4, comment="Tasty soup")
            rating2 = Rating(reservation_id=res2.id, stars=5, comment="")
            db.session.add_all([rating1, rating2])
            db.session.commit()

            reloaded_listing = db.session.get(Listing, listing_id)
            self.assertEqual(len(reloaded_listing.ratings), 2)
            self.assertEqual(reloaded_listing.average_rating, 4.5)
            self.assertEqual(len(reloaded_listing.reviews_with_comments), 1)
            self.assertEqual(reloaded_listing.reviews_with_comments[0].comment, "Tasty soup")

    # Authorization and Access Control Tests

    def test_anonymous_user_cannot_access_rating(self):
        res_id, _ = self.create_reservation(self.alice_id, code="ANO001")
        get_response = self.client.get(f"/student/reservations/{res_id}/rate")
        self.assertEqual(get_response.status_code, 403)

        post_response = self.client.post(
            f"/student/reservations/{res_id}/rate",
            data={"stars": "5", "comment": "Great!"},
        )
        self.assertEqual(post_response.status_code, 403)

    def test_vendor_cannot_access_rating(self):
        res_id, _ = self.create_reservation(self.alice_id, code="VND001")
        self.login_as(self.vendor_id, role="vendor")

        get_response = self.client.get(f"/student/reservations/{res_id}/rate")
        self.assertEqual(get_response.status_code, 403)

        post_response = self.client.post(
            f"/student/reservations/{res_id}/rate",
            data={"stars": "5", "comment": "Great!"},
        )
        self.assertEqual(post_response.status_code, 403)

    def test_student_cannot_rate_another_students_reservation(self):
        res_id, _ = self.create_reservation(self.alice_id, code="OTH001")
        self.login_as(self.bob_id, role="student")

        get_response = self.client.get(f"/student/reservations/{res_id}/rate")
        self.assertEqual(get_response.status_code, 403)

        post_response = self.client.post(
            f"/student/reservations/{res_id}/rate",
            data={"stars": "5", "comment": "Forbidden"},
        )
        self.assertEqual(post_response.status_code, 403)

    def test_rate_nonexistent_reservation_returns_404(self):
        self.login_as(self.alice_id, role="student")
        get_response = self.client.get("/student/reservations/99999/rate")
        self.assertEqual(get_response.status_code, 404)

        post_response = self.client.post(
            "/student/reservations/99999/rate",
            data={"stars": "5"},
        )
        self.assertEqual(post_response.status_code, 404)

    # Eligibility Guard Tests

    def test_cannot_rate_active_reservation(self):
        res_id, _ = self.create_reservation(self.alice_id, status="active", code="ACT001")
        self.login_as(self.alice_id, role="student")

        get_response = self.client.get(
            f"/student/reservations/{res_id}/rate", follow_redirects=True
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertIn(b"Only picked-up reservations can be rated.", get_response.data)

        post_response = self.client.post(
            f"/student/reservations/{res_id}/rate",
            data={"stars": "5"},
            follow_redirects=True,
        )
        self.assertEqual(post_response.status_code, 200)
        self.assertIn(b"Only picked-up reservations can be rated.", post_response.data)

        with self.app.app_context():
            rating = db.session.execute(
                db.select(Rating).filter_by(reservation_id=res_id)
            ).scalar_one_or_none()
            self.assertIsNone(rating)

    def test_cannot_rate_cancelled_reservation(self):
        res_id, _ = self.create_reservation(self.alice_id, status="cancelled", code="CAN001")
        self.login_as(self.alice_id, role="student")

        post_response = self.client.post(
            f"/student/reservations/{res_id}/rate",
            data={"stars": "5"},
            follow_redirects=True,
        )
        self.assertEqual(post_response.status_code, 200)
        self.assertIn(b"Only picked-up reservations can be rated.", post_response.data)

    def test_cannot_rate_no_show_reservation(self):
        res_id, _ = self.create_reservation(self.alice_id, status="no-show", code="NOS001")
        self.login_as(self.alice_id, role="student")

        post_response = self.client.post(
            f"/student/reservations/{res_id}/rate",
            data={"stars": "1"},
            follow_redirects=True,
        )
        self.assertEqual(post_response.status_code, 200)
        self.assertIn(b"Only picked-up reservations can be rated.", post_response.data)

    # Single Rating Rule Tests

    def test_cannot_rate_already_rated_reservation(self):
        res_id, _ = self.create_reservation(self.alice_id, status="picked up", code="SNG001")
        with self.app.app_context():
            existing = Rating(reservation_id=res_id, stars=5, comment="Initial review")
            db.session.add(existing)
            db.session.commit()

        self.login_as(self.alice_id, role="student")

        get_response = self.client.get(
            f"/student/reservations/{res_id}/rate", follow_redirects=True
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertIn(b"You have already rated this reservation.", get_response.data)

        post_response = self.client.post(
            f"/student/reservations/{res_id}/rate",
            data={"stars": "3", "comment": "Trying second review"},
            follow_redirects=True,
        )
        self.assertEqual(post_response.status_code, 200)
        self.assertIn(b"You have already rated this reservation.", post_response.data)

        with self.app.app_context():
            ratings = (
                db.session.execute(db.select(Rating).filter_by(reservation_id=res_id))
                .scalars()
                .all()
            )
            self.assertEqual(len(ratings), 1)
            self.assertEqual(ratings[0].stars, 5)

    # Input Validation Tests

    def test_missing_and_invalid_stars_rejected(self):
        res_id, _ = self.create_reservation(self.alice_id, code="VAL001")
        self.login_as(self.alice_id, role="student")

        missing_res = self.client.post(
            f"/student/reservations/{res_id}/rate",
            data={"stars": "", "comment": "Missing stars"},
        )
        self.assertEqual(missing_res.status_code, 200)
        self.assertIn(b"Star rating must be an integer between 1 and 5.", missing_res.data)

        alpha_res = self.client.post(
            f"/student/reservations/{res_id}/rate",
            data={"stars": "five", "comment": "Word stars"},
        )
        self.assertEqual(alpha_res.status_code, 200)
        self.assertIn(b"Star rating must be an integer between 1 and 5.", alpha_res.data)

        decimal_res = self.client.post(
            f"/student/reservations/{res_id}/rate",
            data={"stars": "4.5", "comment": "Decimal stars"},
        )
        self.assertEqual(decimal_res.status_code, 200)
        self.assertIn(b"Star rating must be an integer between 1 and 5.", decimal_res.data)

        zero_res = self.client.post(
            f"/student/reservations/{res_id}/rate",
            data={"stars": "0"},
        )
        self.assertEqual(zero_res.status_code, 200)
        self.assertIn(b"Star rating must be an integer between 1 and 5.", zero_res.data)

        large_res = self.client.post(
            f"/student/reservations/{res_id}/rate",
            data={"stars": "6"},
        )
        self.assertEqual(large_res.status_code, 200)
        self.assertIn(b"Star rating must be an integer between 1 and 5.", large_res.data)

    def test_comment_exceeding_300_characters_rejected(self):
        res_id, _ = self.create_reservation(self.alice_id, code="VAL002")
        self.login_as(self.alice_id, role="student")

        long_comment = "A" * 301
        response = self.client.post(
            f"/student/reservations/{res_id}/rate",
            data={"stars": "5", "comment": long_comment},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Comment must not exceed 300 characters.", response.data)

        with self.app.app_context():
            rating = db.session.execute(
                db.select(Rating).filter_by(reservation_id=res_id)
            ).scalar_one_or_none()
            self.assertIsNone(rating)

    def test_comment_boundary_300_characters_accepted(self):
        res_id, _ = self.create_reservation(self.alice_id, code="BND001")
        self.login_as(self.alice_id, role="student")

        boundary_comment = "B" * 300
        response = self.client.post(
            f"/student/reservations/{res_id}/rate",
            data={"stars": "5", "comment": boundary_comment},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Thank you for your rating!", response.data)

        with self.app.app_context():
            rating = db.session.execute(
                db.select(Rating).filter_by(reservation_id=res_id)
            ).scalar_one_or_none()
            self.assertIsNotNone(rating)
            self.assertEqual(len(rating.comment), 300)

    # Happy Path Tests

    def test_rate_page_renders_cleanly(self):
        res_id, _ = self.create_reservation(self.alice_id, code="RND001", title="Gourmet Burrito")
        self.login_as(self.alice_id, role="student")

        response = self.client.get(f"/student/reservations/{res_id}/rate")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Rate Your Pickup", response.data)
        self.assertIn(b"Gourmet Burrito", response.data)
        self.assertIn(b"Chef Vendor", response.data)
        self.assertIn(b"RND001", response.data)

    def test_rate_pickup_with_stars_and_comment_success(self):
        res_id, _ = self.create_reservation(self.alice_id, code="HAP001")
        self.login_as(self.alice_id, role="student")

        response = self.client.post(
            f"/student/reservations/{res_id}/rate",
            data={"stars": "4", "comment": "Delicious food and polite staff!"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Thank you for your rating!", response.data)

        with self.app.app_context():
            rating = db.session.execute(
                db.select(Rating).filter_by(reservation_id=res_id)
            ).scalar_one_or_none()
            self.assertIsNotNone(rating)
            self.assertEqual(rating.stars, 4)
            self.assertEqual(rating.comment, "Delicious food and polite staff!")

    def test_rate_pickup_with_stars_only_success(self):
        res_id, _ = self.create_reservation(self.alice_id, code="HAP002")
        self.login_as(self.alice_id, role="student")

        response = self.client.post(
            f"/student/reservations/{res_id}/rate",
            data={"stars": "5", "comment": "   "},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Thank you for your rating!", response.data)

        with self.app.app_context():
            rating = db.session.execute(
                db.select(Rating).filter_by(reservation_id=res_id)
            ).scalar_one_or_none()
            self.assertIsNotNone(rating)
            self.assertEqual(rating.stars, 5)
            self.assertIsNone(rating.comment)

    # Student Reservations View Tests

    def test_my_reservations_view_rating_status(self):
        res1, _ = self.create_reservation(self.alice_id, status="picked up", code="MYR001")
        res2, _ = self.create_reservation(self.alice_id, status="picked up", code="MYR002")
        with self.app.app_context():
            rating = Rating(reservation_id=res1, stars=5)
            db.session.add(rating)
            db.session.commit()

        self.login_as(self.alice_id, role="student")
        response = self.client.get("/student/reservations")
        self.assertEqual(response.status_code, 200)

        # Rated reservation displays rated badge and no rate link
        self.assertIn(b"Rated: 5 \xe2\x98\x85", response.data)
        self.assertNotIn(f"/student/reservations/{res1}/rate".encode(), response.data)

        # Unrated reservation displays rate pickup button
        self.assertIn(f"/student/reservations/{res2}/rate".encode(), response.data)
        self.assertIn(b"Rate Pickup", response.data)

    # Vendor Listings View Tests

    def test_vendor_listings_displays_ratings_and_comments(self):
        res1, listing_id = self.create_reservation(
            self.alice_id,
            status="picked up",
            vendor_id=self.vendor_id,
            code="VND011",
            title="Vendor Special Rice",
        )

        with self.app.app_context():
            res2 = Reservation(
                student_id=self.bob_id,
                listing_id=listing_id,
                portions_reserved=1,
                pickup_code="VND012",
                status="picked up",
            )
            db.session.add(res2)
            db.session.flush()

            rating1 = Rating(
                reservation_id=res1,
                stars=5,
                comment="Super fresh and generous portions!",
            )
            rating2 = Rating(
                reservation_id=res2.id,
                stars=4,
                comment="Very tasty dinner",
            )
            db.session.add_all([rating1, rating2])
            db.session.commit()

        fake_vendor = SimpleNamespace(
            id=self.vendor_id,
            is_authenticated=True,
            role="vendor",
            name="Chef Vendor",
        )
        patcher = patch("campuseats.routes.vendor.current_user", fake_vendor)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher_guard = patch("campuseats.routes.role_guards.current_user", fake_vendor)
        patcher_guard.start()
        self.addCleanup(patcher_guard.stop)

        response = self.client.get("/vendor/listings")
        self.assertEqual(response.status_code, 200)

        # Verify average rating appears
        self.assertIn(b"4.5", response.data)
        self.assertIn(b"Rating & Reviews", response.data)

        # Student review comments must appear
        self.assertIn(b"Super fresh and generous portions!", response.data)
        self.assertIn(b"Very tasty dinner", response.data)

    def test_rate_pickup_integrity_error_handled(self):
        res_id, _ = self.create_reservation(self.alice_id, code="INT001")
        self.login_as(self.alice_id, role="student")

        with patch(
            "campuseats.extensions.db.session.commit",
            side_effect=IntegrityError("duplicate", None, None),
        ):
            response = self.client.post(
                f"/student/reservations/{res_id}/rate",
                data={"stars": "5"},
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"You have already rated this reservation.", response.data)

    def test_vendor_listings_unrated_listing(self):
        self.create_reservation(
            self.alice_id,
            status="active",
            vendor_id=self.vendor_id,
            code="UNR001",
            title="Unrated Listing",
        )
        fake_vendor = SimpleNamespace(
            id=self.vendor_id,
            is_authenticated=True,
            role="vendor",
            name="Chef Vendor",
        )
        patcher = patch("campuseats.routes.vendor.current_user", fake_vendor)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher_guard = patch("campuseats.routes.role_guards.current_user", fake_vendor)
        patcher_guard.start()
        self.addCleanup(patcher_guard.stop)

        response = self.client.get("/vendor/listings")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No ratings yet", response.data)
        self.assertIn(b"No comments", response.data)

    def test_vendor_isolation_reviews(self):
        # Create listing and review for other vendor
        res_other, _ = self.create_reservation(
            self.alice_id,
            status="picked up",
            vendor_id=self.other_vendor_id,
            code="ISO001",
            title="Other Vendor Delicacy",
        )
        with self.app.app_context():
            rating = Rating(
                reservation_id=res_other,
                stars=5,
                comment="Confidential comment for other vendor",
            )
            db.session.add(rating)
            db.session.commit()

        # Log in as primary vendor
        fake_vendor = SimpleNamespace(
            id=self.vendor_id,
            is_authenticated=True,
            role="vendor",
            name="Chef Vendor",
        )
        patcher = patch("campuseats.routes.vendor.current_user", fake_vendor)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher_guard = patch("campuseats.routes.role_guards.current_user", fake_vendor)
        patcher_guard.start()
        self.addCleanup(patcher_guard.stop)

        response = self.client.get("/vendor/listings")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Confidential comment for other vendor", response.data)
        self.assertNotIn(b"Other Vendor Delicacy", response.data)

    def test_vendor_my_listings_template_renders(self):
        from flask import render_template
        from flask_login import login_user

        with self.app.test_request_context():
            fake_vendor = User(
                id=self.vendor_id,
                name="Chef Vendor",
                email="vendor@example.invalid",
                password_hash="fake",
                role="vendor",
            )
            login_user(fake_vendor)
            html = render_template("vendor/my_listings.html", listings=[])
            self.assertIn("My Surplus Food Listings", html)
