import secrets
import string
from campuseats.extensions import db

RESERVATION_STATUSES = (
    "active",
    "picked up",
    "cancelled",
    "no-show",
)

PICKUP_CODE_ALPHABET = string.ascii_uppercase + string.digits


def generate_unique_pickup_code(session, length=6):
    """Generate a random uppercase alphanumeric pickup code unique in the reservations table."""
    max_attempts = 100
    for _ in range(max_attempts):
        code = "".join(secrets.choice(PICKUP_CODE_ALPHABET) for _ in range(length))
        existing = session.execute(
            db.select(Reservation.id).filter_by(pickup_code=code)
        ).scalar_one_or_none()
        if existing is None:
            return code

    raise RuntimeError("Failed to generate a unique pickup code after multiple attempts.")


class Reservation(db.Model):
    __tablename__ = "reservations"
    __table_args__ = (
        db.CheckConstraint(
            "portions_reserved >= 1 AND portions_reserved <= 2",
            name="ck_reservations_portions_reserved_range",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    listing_id = db.Column(
        db.Integer,
        db.ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    portions_reserved = db.Column(db.Integer, nullable=False)
    pickup_code = db.Column(db.String(6), unique=True, nullable=False)
    status = db.Column(
        db.String(20),
        nullable=False,
        default="active",
        server_default="active",
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.current_timestamp(),
    )

    student = db.relationship("User", back_populates="reservations")
    listing = db.relationship("Listing", back_populates="reservations")

    def __repr__(self):
        return f"<Reservation {self.id} {self.pickup_code} ({self.status})>"
