from datetime import datetime

from flask import Blueprint, render_template
from sqlalchemy.orm import selectinload

from campuseats.extensions import db
from campuseats.models.listing import Listing
from campuseats.routes.role_guards import student_required

student_bp = Blueprint("student", __name__)


@student_bp.get("/listings")
@student_required
def listings():
    # Pickup times are stored as naive local datetimes (see routes/vendor.py).
    now = datetime.now()
    stmt = (
        db.select(Listing)
        .where(
            Listing.status == "active",
            Listing.remaining_portions > 0,
            Listing.pickup_end > now,
        )
        .order_by(Listing.pickup_end.asc())
        .options(selectinload(Listing.vendor), selectinload(Listing.tags))
    )
    active = db.session.execute(stmt).scalars().all()
    return render_template("student/listings.html", listings=active)
