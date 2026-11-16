import sys
from pathlib import Path
import unittest

# Ensure Python can find the campuseats package
src_path = str(Path(__file__).resolve().parent.parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from werkzeug.security import check_password_hash

from campuseats import create_app
from campuseats.config import TestingConfig
from campuseats.extensions import db
from campuseats.models.listing import Listing
from campuseats.models.user import User
from campuseats.seed import seed_database


class SeedDatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_seed_database_creates_vendor_and_student_accounts(self):
        with self.app.app_context():
            # Run the seeding logic
            seed_database()

            # Verify vendor account was created
            vendor = db.session.execute(
                db.select(User).filter_by(email="vendor@campuseats.edu")
            ).scalar_one_or_none()
            self.assertIsNotNone(vendor)
            self.assertEqual(vendor.role, "vendor")
            self.assertEqual(vendor.name, "Campus Bakery")
            self.assertTrue(check_password_hash(vendor.password_hash, "Vendor123!"))

            # Verify student account was created
            student = db.session.execute(
                db.select(User).filter_by(email="student@campuseats.edu")
            ).scalar_one_or_none()
            self.assertIsNotNone(student)
            self.assertEqual(student.role, "student")
            self.assertEqual(student.name, "Alex Student")
            self.assertTrue(check_password_hash(student.password_hash, "Student123!"))

            # Verify realistic surplus listings were created
            listings = db.session.execute(db.select(Listing)).scalars().all()
            self.assertEqual(len(listings), 4)
            for item in listings:
                self.assertEqual(item.vendor_id, vendor.id)
                self.assertEqual(item.status, "active")
                self.assertGreater(len(item.tags), 0)

    def test_seed_database_idempotent_when_users_already_exist(self):
        with self.app.app_context():
            seed_database()
            initial_count = len(db.session.execute(db.select(User)).scalars().all())
            initial_listings_count = len(db.session.execute(db.select(Listing)).scalars().all())

            # Second call should safely no-op without adding duplicate users or listings
            seed_database()
            subsequent_count = len(db.session.execute(db.select(User)).scalars().all())
            subsequent_listings_count = len(db.session.execute(db.select(Listing)).scalars().all())

            self.assertEqual(initial_count, subsequent_count)
            self.assertEqual(subsequent_count, 2)
            self.assertEqual(initial_listings_count, subsequent_listings_count)
            self.assertEqual(subsequent_listings_count, 4)

    def test_create_app_seeds_when_configured(self):
        class SeedConfig(TestingConfig):
            SEED_DEMO_USERS = True

        app = create_app(SeedConfig)
        with app.app_context():
            users = db.session.execute(db.select(User)).scalars().all()
            self.assertEqual(len(users), 2)
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_seed_database_restocks_with_new_listings_when_all_expired(self):
        from datetime import datetime, timedelta, timezone

        with self.app.app_context():
            seed_database()
            now = datetime.now(timezone.utc)
            ended_at = now - timedelta(hours=1)
            # Expire all listings
            listings = db.session.execute(db.select(Listing)).scalars().all()
            for item in listings:
                item.pickup_end = ended_at
            db.session.commit()
            old_ids = {item.id for item in listings}

            # Calling seed_database again should post fresh listings so the feed is not empty
            seed_database()
            db.session.expire_all()
            all_listings = db.session.execute(db.select(Listing)).scalars().all()
            self.assertEqual(len(all_listings), 8)
            for item in all_listings:
                if item.id in old_ids:
                    # History is untouched: the old listings still ended when they ended
                    self.assertEqual(item.pickup_end, ended_at)
                    self.assertEqual(item.display_status, "ended")
                else:
                    self.assertGreater(item.pickup_end, now)
                    self.assertEqual(item.display_status, "active")
                    self.assertEqual(item.remaining_portions, item.total_portions)

    def test_seed_database_never_reopens_an_ended_listing_with_reservations(self):
        from datetime import datetime, timedelta, timezone

        from campuseats.models.reservation import Reservation

        with self.app.app_context():
            seed_database()
            now = datetime.now(timezone.utc)
            vendor = db.session.execute(
                db.select(User).filter_by(email="vendor@campuseats.edu")
            ).scalar_one()
            student = db.session.execute(
                db.select(User).filter_by(email="student@campuseats.edu")
            ).scalar_one()
            for item in db.session.execute(db.select(Listing)).scalars().all():
                item.pickup_end = now - timedelta(hours=1)

            # A listing the vendor posted by hand, now ended, with a reservation nobody collected
            manual = Listing(
                vendor_id=vendor.id,
                title="Yesterday's Sandwiches",
                total_portions=3,
                remaining_portions=1,
                pickup_location="Student Union",
                pickup_start=now - timedelta(hours=5),
                pickup_end=now - timedelta(hours=2),
                status="active",
            )
            db.session.add(manual)
            db.session.flush()
            reservation = Reservation(
                student_id=student.id,
                listing_id=manual.id,
                portions_reserved=2,
                pickup_code="OLD001",
                status="active",
            )
            db.session.add(reservation)
            db.session.commit()
            manual_id, reservation_id = manual.id, reservation.id

            seed_database()
            db.session.expire_all()

            manual = db.session.get(Listing, manual_id)
            self.assertEqual(manual.display_status, "ended")
            self.assertEqual(manual.remaining_portions, 1)
            self.assertEqual(db.session.get(Reservation, reservation_id).display_status, "no-show")

    def test_seed_database_does_not_restock_while_a_listing_is_still_open(self):
        with self.app.app_context():
            seed_database()
            # Even with every other listing cancelled, one open listing keeps the feed populated
            listings = db.session.execute(db.select(Listing)).scalars().all()
            for item in listings[1:]:
                item.status = "cancelled"
            db.session.commit()

            seed_database()
            self.assertEqual(len(db.session.execute(db.select(Listing)).scalars().all()), 4)

    def test_create_app_does_not_seed_by_default_in_testing(self):
        with self.app.app_context():
            users = db.session.execute(db.select(User)).scalars().all()
            self.assertEqual(len(users), 0)


if __name__ == "__main__":
    unittest.main()
