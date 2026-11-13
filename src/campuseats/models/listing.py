from campuseats.extensions import db

DEFAULT_DIETARY_TAGS = (
    "vegetarian",
    "vegan",
    "gluten-free",
    "halal",
    "contains nuts",
)

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
    pickup_start = db.Column(db.DateTime, nullable=False)
    pickup_end = db.Column(db.DateTime, nullable=False)
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
    def ratings(self):
        """Retrieve all rating records associated with reservations for this listing."""
        return [res.rating for res in self.reservations if getattr(res, "rating", None) is not None]

    @property
    def average_rating(self):
        """Compute average star rating, returning None when no ratings exist."""
        all_ratings = self.ratings
        if not all_ratings:
            return None
        return round(sum(r.stars for r in all_ratings) / len(all_ratings), 1)

    @property
    def reviews_with_comments(self):
        """Retrieve ratings that contain non-empty comment text."""
        return [r for r in self.ratings if r.comment and r.comment.strip()]

    def __repr__(self):
        return f"<Listing {self.title}>"
