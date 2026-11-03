from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from campuseats.extensions import db
from campuseats.models.listing import Listing
from campuseats.models.reservation import Reservation, generate_unique_pickup_code
from campuseats.routes.role_guards import student_required

student_bp = Blueprint("student", __name__)


@student_bp.route("/listings", methods=["GET"])
@student_required
def listings():
    # Retrieve active surplus food listings whose pickup windows have not yet elapsed
    now = datetime.now()
    available_listings = (
        db.session.execute(
            db.select(Listing)
            .options(selectinload(Listing.vendor), selectinload(Listing.tags))
            .filter(
                Listing.status == "active",
                Listing.remaining_portions > 0,
                Listing.pickup_end > now,
            )
            .order_by(Listing.pickup_end.asc())
        )
        .scalars()
        .all()
    )

    # Map current student's active reservations by listing for convenient card status display
    active_reservations = (
        db.session.execute(
            db.select(Reservation).filter_by(
                student_id=current_user.id,
                status="active",
            )
        )
        .scalars()
        .all()
    )
    active_reservations_by_listing = {res.listing_id: res for res in active_reservations}

    # Check for freshly created reservation to display in pickup confirmation modal
    recent_reservation_id = session.pop("recent_reservation_id", None)
    recent_reservation = None
    if recent_reservation_id:
        recent_reservation = db.session.execute(
            db.select(Reservation)
            .options(selectinload(Reservation.listing).selectinload(Listing.vendor))
            .filter_by(id=recent_reservation_id, student_id=current_user.id)
        ).scalar_one_or_none()

    return render_template(
        "student/listings.html",
        listings=available_listings,
        active_reservations_by_listing=active_reservations_by_listing,
        recent_reservation=recent_reservation,
    )


@student_bp.route("/listings/<int:listing_id>/reserve", methods=["POST"])
@student_required
def reserve_listing(listing_id):
    # Validate portions input format and permissible quantity range
    portions_raw = request.form.get("portions", "").strip()
    try:
        portions = int(portions_raw)
        if portions not in (1, 2):
            raise ValueError
    except (ValueError, TypeError):
        flash("Please select either 1 or 2 portions to reserve.", "danger")
        return redirect(url_for("student.listings"))

    # Acquire listing record with row locking to ensure concurrent booking safety
    listing = db.session.execute(
        db.select(Listing).filter_by(id=listing_id).with_for_update()
    ).scalar_one_or_none()

    now = datetime.now()
    if listing is None or listing.status != "active" or listing.pickup_end <= now:
        db.session.rollback()
        flash("This listing is no longer available for reservation.", "danger")
        return redirect(url_for("student.listings"))

    # Enforce that a student may only hold one active reservation per listing
    existing_active = db.session.execute(
        db.select(Reservation).filter_by(
            student_id=current_user.id,
            listing_id=listing.id,
            status="active",
        )
    ).scalar_one_or_none()

    if existing_active is not None:
        db.session.rollback()
        flash("You already have an active reservation for this listing.", "danger")
        return redirect(url_for("student.listings"))

    # Verify inventory is sufficient to fulfill requested portion count
    if listing.remaining_portions < portions or listing.remaining_portions <= 0:
        db.session.rollback()
        flash("Not enough portions remaining to fulfill your request.", "danger")
        return redirect(url_for("student.listings"))

    # Generate unique 6-character pickup code and commit inventory update inside transaction
    try:
        pickup_code = generate_unique_pickup_code(db.session)
        listing.remaining_portions -= portions

        new_reservation = Reservation(
            student_id=current_user.id,
            listing_id=listing.id,
            portions_reserved=portions,
            pickup_code=pickup_code,
            status="active",
        )
        db.session.add(new_reservation)
        db.session.commit()
    except (IntegrityError, RuntimeError):
        db.session.rollback()
        flash("An error occurred while confirming your reservation. Please try again.", "danger")
        return redirect(url_for("student.listings"))

    # Store reservation id in session so browse feed renders confirmation modal
    session["recent_reservation_id"] = new_reservation.id
    flash(f"Reservation confirmed! Your pickup code is {pickup_code}.", "success")
    return redirect(url_for("student.listings"))
