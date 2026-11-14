from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

from campuseats.extensions import db
from campuseats.models.listing import DEFAULT_DIETARY_TAGS, DietaryTag, Listing
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
    db.session.flush()

    # Pre-populate canonical dietary tags
    tag_map = {}
    for tag_name in DEFAULT_DIETARY_TAGS:
        tag = db.session.execute(
            db.select(DietaryTag).filter_by(name=tag_name)
        ).scalar_one_or_none()
        if tag is None:
            tag = DietaryTag(name=tag_name)
            db.session.add(tag)
            db.session.flush()
        tag_map[tag_name] = tag

    # Seed realistic surplus food listings
    now = datetime.now(timezone.utc)
    sample_listings = [
        Listing(
            vendor_id=sample_vendor.id,
            title="Fresh Morning Bagels & Pastries",
            description=(
                "Surplus morning bake featuring plain, everything, and cinnamon raisin bagels, "
                "plus fresh blueberry muffins."
            ),
            total_portions=12,
            remaining_portions=12,
            pickup_location="Student Union - Bakery Counter",
            pickup_start=now - timedelta(minutes=30),
            pickup_end=now + timedelta(hours=3),
            status="active",
            tags=[tag_map["vegetarian"], tag_map["contains nuts"]],
        ),
        Listing(
            vendor_id=sample_vendor.id,
            title="Artisan Sourdough & Herb Focaccia",
            description=(
                "Freshly baked sourdough batards and rosemary sea-salt focaccia loaves packaged "
                "for takeaway."
            ),
            total_portions=8,
            remaining_portions=8,
            pickup_location="North Dining Hall - Cafe Entrance",
            pickup_start=now - timedelta(minutes=45),
            pickup_end=now + timedelta(hours=4),
            status="active",
            tags=[tag_map["vegetarian"], tag_map["vegan"]],
        ),
        Listing(
            vendor_id=sample_vendor.id,
            title="Mediterranean Falafel & Hummus Bowls",
            description=(
                "Fresh falafel patties over spiced brown rice with house hummus, chopped "
                "cucumber-tomato salad, and warm pita bread."
            ),
            total_portions=10,
            remaining_portions=10,
            pickup_location="Global Eats Food Court - Station 2",
            pickup_start=now - timedelta(minutes=15),
            pickup_end=now + timedelta(hours=2),
            status="active",
            tags=[tag_map["vegetarian"], tag_map["vegan"], tag_map["halal"]],
        ),
        Listing(
            vendor_id=sample_vendor.id,
            title="Hearty Vegetable Minestrone Soup & Rolls",
            description=(
                "Slow-simmered vegetable minestrone soup with cannellini beans, kale, and "
                "seasonal vegetables, served with warm gluten-free rolls."
            ),
            total_portions=6,
            remaining_portions=6,
            pickup_location="Commons Dining - Soup & Salad Station",
            pickup_start=now - timedelta(minutes=20),
            pickup_end=now + timedelta(hours=2, minutes=30),
            status="active",
            tags=[
                tag_map["vegetarian"],
                tag_map["vegan"],
                tag_map["gluten-free"],
                tag_map["halal"],
            ],
        ),
    ]

    db.session.add_all(sample_listings)
    db.session.commit()
