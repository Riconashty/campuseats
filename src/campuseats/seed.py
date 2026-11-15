from werkzeug.security import generate_password_hash

from campuseats.extensions import db
from campuseats.models.user import User


def seed_database():
    # Check if database already has user accounts populated
    existing_user = db.session.execute(db.select(User)).first()
    if existing_user is not None:
        return

    # Seed baseline vendor and student accounts for grading and testing
    sample_vendor = User(
        name="Campus Bakery",
        email="vendor@campuseats.edu",
        password_hash=generate_password_hash("Vendor123!"),
        role="vendor",
    )
    sample_student = User(
        name="Alex Student",
        email="student@campuseats.edu",
        password_hash=generate_password_hash("Student123!"),
        role="student",
    )

    db.session.add_all([sample_vendor, sample_student])
    db.session.commit()
