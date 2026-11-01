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

    def test_seed_database_idempotent_when_users_already_exist(self):
        with self.app.app_context():
            seed_database()
            initial_count = len(db.session.execute(db.select(User)).scalars().all())

            # Second call should safely no-op without adding duplicate users
            seed_database()
            subsequent_count = len(db.session.execute(db.select(User)).scalars().all())

            self.assertEqual(initial_count, subsequent_count)
            self.assertEqual(subsequent_count, 2)


if __name__ == "__main__":
    unittest.main()
