from datetime import datetime, timezone

from campuseats.extensions import db

DEFAULT_DIETARY_TAGS = (
    "vegetarian",
    "vegan",
    "gluten-free",
    "halal",
    "contains nuts",
)


class UTCDateTime(db.TypeDecorator):
    """DateTime type that standardizes storage and retrieval using timezone-aware UTC timestamps."""

    impl = db.DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                return value.astimezone(timezone.utc)
            return value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


# Association table between listings and dietary tags
listing_dietary_tags = db.Table(
    "listing_dietary_tags",
    db.Column(
        "listing_id",
        db.Integer,
        db.ForeignKey("listings.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "dietary_tag_id",
        db.Integer,
        db.ForeignKey("dietary_tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class DietaryTag(db.Model):
    __tablename__ = "dietary_tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def __repr__(self):
        return f"<DietaryTag {self.name}>"


class Listing(db.Model):
    __tablename__ = "listings"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    total_portions = db.Column(db.Integer, nullable=False)
    remaining_portions = db.Column(db.Integer, nullable=False)
    pickup_location = db.Column(db.String(255), nullable=False)
    pickup_start = db.Column(UTCDateTime, nullable=False)
    pickup_end = db.Column(UTCDateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active", server_default="active")
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.current_timestamp(),
    )

    vendor = db.relationship("User", back_populates="listings")
    reservations = db.relationship(
        "Reservation",
        back_populates="listing",
        cascade="all, delete-orphan",
    )
    tags = db.relationship(
        "DietaryTag",
        secondary=listing_dietary_tags,
        backref=db.backref("listings", lazy="dynamic"),
    )

    @property
    def reserved_portions(self):
        return self.total_portions - self.remaining_portions

    @property
    def display_status(self):
        end = self.pickup_end
        if end is not None:
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            if self.status == "active" and end <= datetime.now(timezone.utc):
                return "ended"
        return self.status

    def __repr__(self):
        return f"<Listing {self.title}>"
