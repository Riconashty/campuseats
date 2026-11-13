from datetime import datetime
from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user
from sqlalchemy import case
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from campuseats.extensions import db
from campuseats.models.listing import Listing
from campuseats.models.rating import Rating
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
    user_id = getattr(current_user, "id", None)
    active_reservations_by_listing = {}
    if user_id:
        active_reservations = (
            db.session.execute(
                db.select(Reservation).filter_by(
                    student_id=user_id,
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
    if recent_reservation_id and user_id:
        recent_reservation = db.session.execute(
            db.select(Reservation)
            .options(selectinload(Reservation.listing).selectinload(Listing.vendor))
            .filter_by(id=recent_reservation_id, student_id=user_id)
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
    user_id = getattr(current_user, "id", None)
    existing_active = db.session.execute(
        db.select(Reservation).filter_by(
            student_id=user_id,
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
            student_id=user_id,
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


@student_bp.route("/student/reservations", methods=["GET"])
@student_required
def my_reservations():
    reservations = (
        db.session.execute(
            db.select(Reservation)
            .options(
                selectinload(Reservation.listing).selectinload(Listing.vendor),
                selectinload(Reservation.rating),
            )
            .filter_by(student_id=current_user.id)
            .order_by(
                case((Reservation.status == "active", 0), else_=1),
                Reservation.created_at.desc(),
            )
        )
        .scalars()
        .all()
    )
    return render_template(
        "student/my_reservations.html",
        reservations=reservations,
        now=datetime.now(),
    )


@student_bp.route("/student/reservations/<int:reservation_id>/rate", methods=["GET", "POST"])
@student_required
def rate_reservation(reservation_id):
    # Query reservation with associated listing, vendor, and existing rating
    reservation = db.session.execute(
        db.select(Reservation)
        .options(
            selectinload(Reservation.listing).selectinload(Listing.vendor),
            selectinload(Reservation.rating),
        )
        .filter_by(id=reservation_id)
    ).scalar_one_or_none()

    # Verify reservation existence
    if reservation is None:
        abort(404)

    # Restrict access to owning student
    if reservation.student_id != current_user.id:
        abort(403)

    # Enforce eligibility guard so only picked up reservations can be rated
    if reservation.status != "picked up":
        flash("Only picked-up reservations can be rated.", "danger")
        return redirect(url_for("student.my_reservations"))

    # Prevent duplicate ratings for the same reservation
    if reservation.rating is not None:
        flash("You have already rated this reservation.", "danger")
        return redirect(url_for("student.my_reservations"))

    if request.method == "POST":
        stars_raw = request.form.get("stars", "").strip()
        comment = request.form.get("comment", "").strip()

        # Validate star rating format and bounds
        try:
            stars = int(stars_raw)
            if stars < 1 or stars > 5:
                raise ValueError
        except (ValueError, TypeError):
            flash("Star rating must be an integer between 1 and 5.", "danger")
            return render_template(
                "student/rate.html",
                reservation=reservation,
                stars=stars_raw,
                comment=comment,
            )

        # Validate comment length limit
        if len(comment) > 300:
            flash("Comment must not exceed 300 characters.", "danger")
            return render_template(
                "student/rate.html",
                reservation=reservation,
                stars=stars,
                comment=comment,
            )

        # Persist rating record and handle concurrent duplicate race conditions
        new_rating = Rating(
            reservation_id=reservation.id,
            stars=stars,
            comment=comment if comment else None,
        )

        try:
            db.session.add(new_rating)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("You have already rated this reservation.", "danger")
            return redirect(url_for("student.my_reservations"))

        flash("Thank you for your rating!", "success")
        return redirect(url_for("student.my_reservations"))

    return render_template(
        "student/rate.html",
        reservation=reservation,
        stars=None,
        comment="",
    )


@student_bp.route("/student/reservations/<int:reservation_id>/cancel", methods=["POST"])
@student_required
def cancel_reservation(reservation_id):
    # Lock the reservation first so two simultaneous cancels cannot both succeed
    reservation = db.session.execute(
        db.select(Reservation).filter_by(id=reservation_id).with_for_update()
    ).scalar_one_or_none()

    if reservation is None:
        db.session.rollback()
        abort(404)
    if reservation.student_id != current_user.id:
        db.session.rollback()
        abort(403)

    # Then lock the listing, the same way reserve_listing does
    listing = db.session.execute(
        db.select(Listing).filter_by(id=reservation.listing_id).with_for_update()
    ).scalar_one()

    if reservation.status != "active" or listing.pickup_end <= datetime.now():
        db.session.rollback()
        flash("This reservation can no longer be cancelled.", "danger")
        return redirect(url_for("student.my_reservations"))

    reservation.status = "cancelled"
    listing.remaining_portions += reservation.portions_reserved
    db.session.commit()

    flash("Reservation cancelled. Your portions were released.", "success")
    return redirect(url_for("student.my_reservations"))
