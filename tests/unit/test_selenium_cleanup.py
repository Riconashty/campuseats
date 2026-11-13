from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from campuseats import create_app
from campuseats.config import TestingConfig
from campuseats.extensions import db
from campuseats.models.listing import Listing
from campuseats.models.reservation import Reservation
from campuseats.models.user import User


class SeleniumCleanupUnitTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_cleanup_test_database_removes_tracked_and_pattern_listings(self):
        with self.app.app_context():
            vendor = User(
                name="Selenium Vendor",
                email="vendor_test@campuseats.edu",
                password_hash="x",
                role="vendor",
            )
            student = User(
                name="Selenium Student",
                email="student_test@campuseats.edu",
                password_hash="x",
                role="student",
            )
            legit_vendor = User(
                name="Campus Bakery",
                email="bakery@campuseats.edu",
                password_hash="x",
                role="vendor",
            )
            db.session.add_all([vendor, student, legit_vendor])
            db.session.commit()

            now = datetime.now(timezone.utc)
            test_listing_1 = Listing(
                vendor_id=vendor.id,
                title="Fresh Sandwiches a1b2c3",
                total_portions=5,
                remaining_portions=4,
                pickup_location="Student Union",
                pickup_start=now,
                pickup_end=now + timedelta(hours=2),
            )
            test_listing_2 = Listing(
                vendor_id=vendor.id,
                title="Last Bagel d4e5f6",
                total_portions=3,
                remaining_portions=3,
                pickup_location="Dining Hall",
                pickup_start=now,
                pickup_end=now + timedelta(hours=2),
            )
            tracked_listing = Listing(
                vendor_id=vendor.id,
                title="Tracked Test Item 99",
                total_portions=2,
                remaining_portions=2,
                pickup_location="Cafe",
                pickup_start=now,
                pickup_end=now + timedelta(hours=2),
            )
            legit_listing = Listing(
                vendor_id=legit_vendor.id,
                title="Cheese Bread",
                total_portions=8,
                remaining_portions=8,
                pickup_location="Bakery Counter",
                pickup_start=now,
                pickup_end=now + timedelta(hours=2),
            )
            db.session.add_all([test_listing_1, test_listing_2, tracked_listing, legit_listing])
            db.session.commit()

            res = Reservation(
                student_id=student.id,
                listing_id=test_listing_1.id,
                portions_reserved=1,
                pickup_code="CLN123",
                status="active",
            )
            db.session.add(res)
            db.session.commit()

            from tests.integration.test_us4_selenium import TestUS4SeleniumBlackBox

            TestUS4SeleniumBlackBox.created_listing_titles = ["Tracked Test Item 99"]
            TestUS4SeleniumBlackBox.cleanup_test_database(app=self.app)

            remaining_listings = db.session.execute(db.select(Listing)).scalars().all()
            remaining_titles = [item.title for item in remaining_listings]

            self.assertIn("Cheese Bread", remaining_titles)
            self.assertNotIn("Fresh Sandwiches a1b2c3", remaining_titles)
            self.assertNotIn("Last Bagel d4e5f6", remaining_titles)
            self.assertNotIn("Tracked Test Item 99", remaining_titles)

            remaining_res = (
                db.session.execute(db.select(Reservation).filter_by(pickup_code="CLN123"))
                .scalars()
                .all()
            )
            self.assertEqual(len(remaining_res), 0)

            remaining_test_users = (
                db.session.execute(
                    db.select(User).filter(
                        User.email.in_(
                            ["vendor_test@campuseats.edu", "student_test@campuseats.edu"]
                        )
                    )
                )
                .scalars()
                .all()
            )
            self.assertEqual(len(remaining_test_users), 0)

            remaining_legit_user = (
                db.session.execute(db.select(User).filter_by(email="bakery@campuseats.edu"))
                .scalars()
                .first()
            )
            self.assertIsNotNone(remaining_legit_user)
