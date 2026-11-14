from campuseats.extensions import db


class Rating(db.Model):
    __tablename__ = "ratings"
    __table_args__ = (
        db.CheckConstraint(
            "stars >= 1 AND stars <= 5",
            name="ck_ratings_stars_range",
        ),
        db.CheckConstraint(
            "comment IS NULL OR length(comment) <= 300",
            name="ck_ratings_comment_length",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(
        db.Integer,
        db.ForeignKey("reservations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    stars = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(300), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.current_timestamp(),
    )

    reservation = db.relationship("Reservation", back_populates="rating")

    def __repr__(self):
        return f"<Rating {self.id} for Reservation {self.reservation_id} ({self.stars} stars)>"
