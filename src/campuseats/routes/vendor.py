from datetime import datetime
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.orm import selectinload

from campuseats.extensions import db
from campuseats.models.listing import DEFAULT_DIETARY_TAGS, DietaryTag, Listing
from campuseats.models.reservation import Reservation
from campuseats.routes.role_guards import vendor_required

vendor_bp = Blueprint("vendor", __name__)


def _validate_listing_form(form):
    """
    Check a submitted listing form against the US2 rules.
    Returns (data, error). If the form is valid, data is a dict of cleaned values and
    error is None. If not, data is None and error is the message to flash.
    """
    title = form.get("title", "").strip()
    description = form.get("description", "").strip()
    portions_raw = form.get("portions", "").strip()
    pickup_location = form.get("pickup_location", "").strip()
    pickup_start_raw = form.get("pickup_start", "").strip()
    pickup_end_raw = form.get("pickup_end", "").strip()

    required_fields = {
        "Title": title,
        "Portions": portions_raw,
        "Pickup Location": pickup_location,
        "Pickup Start": pickup_start_raw,
        "Pickup End": pickup_end_raw,
    }

    for field_name, value in required_fields.items():
        if not value:
            return None, f"Please complete all required fields. Missing: {field_name}."

    try:
        portions = int(portions_raw)
        if portions < 1 or portions > 100:
            raise ValueError
    except ValueError:
        return None, "Portions must be an integer between 1 and 100."

    try:
        pickup_start = datetime.fromisoformat(pickup_start_raw)
        pickup_end = datetime.fromisoformat(pickup_end_raw)
    except ValueError:
        return None, "Please provide valid dates and times for the pickup window."

    if pickup_end < datetime.now():
        return None, "Pickup end time cannot be in the past."

    if pickup_end <= pickup_start:
        return None, "Pickup end time must be after pickup start time."

    data = {
        "title": title,
        "description": description if description else None,
        "portions": portions,
        "pickup_location": pickup_location,
        "pickup_start": pickup_start,
        "pickup_end": pickup_end,
    }

    return data, None


def _resolve_dietary_tags(selected_tags):
    # Resolve validated dietary tags
    tags_to_attach = []
    for tag_name in set(selected_tags):
        tag_name_clean = tag_name.strip().lower()
        if tag_name_clean in DEFAULT_DIETARY_TAGS:
            tag = db.session.execute(
                db.select(DietaryTag).filter_by(name=tag_name_clean)
            ).scalar_one_or_none()
            if not tag:
                tag = DietaryTag(name=tag_name_clean)
                db.session.add(tag)
            tags_to_attach.append(tag)
    return tags_to_attach


def _get_owned_listing(listing_id, lock=False):
    """Return the listing if the logged-in vendor owns it; otherwise stop with 404 or 403."""
    query = db.select(Listing).filter_by(id=listing_id)
    if lock:
        # Same row lock reserve_listing() takes, so reservations wait until this request is done
        query = query.with_for_update()
    listing = db.session.execute(query).scalar_one_or_none()

    if listing is None:
        db.session.rollback()
        abort(404)
    if listing.vendor_id != current_user.id:
        db.session.rollback()
        abort(403)
    return listing


@vendor_bp.route("/vendor/listings", methods=["GET"])
@vendor_required
def vendor_listings():
    # Retrieve all listings posted by the current vendor
    listings = (
        db.session.execute(
            db.select(Listing)
            .filter_by(vendor_id=current_user.id)
            .order_by(Listing.created_at.desc())
        )
        .scalars()
        .all()
    )
    return render_template("vendor/my_listings.html", listings=listings)


@vendor_bp.route("/vendor/listings/<int:listing_id>", methods=["GET"])
@vendor_required
def listing_detail(listing_id):
    listing = _get_owned_listing(listing_id)

    # Every reservation on this listing, oldest first, with its student loaded
    reservations = (
        db.session.execute(
            db.select(Reservation)
            .options(selectinload(Reservation.student))
            .filter_by(listing_id=listing.id)
            .order_by(Reservation.id)
        )
        .scalars()
        .all()
    )
    return render_template(
        "vendor/listing_detail.html",
        listing=listing,
        reservations=reservations,
    )


@vendor_bp.route("/vendor/listings/<int:listing_id>/edit", methods=["GET", "POST"])
@vendor_required
def edit_listing(listing_id):
    # Only a POST changes data, so only a POST needs the row lock
    listing = _get_owned_listing(listing_id, lock=request.method == "POST")

    # Ended and cancelled listings are read-only
    if listing.display_status != "active":
        db.session.rollback()
        flash("Only active listings can be edited.", "danger")
        return redirect(url_for("vendor.vendor_listings"))

    if request.method == "POST":
        selected_tags = request.form.getlist("dietary_tags")
        reserved = listing.reserved_portions
        data, error = _validate_listing_form(request.form)

        # Portion reduction guard
        if error is None and data["portions"] < reserved:
            error = f"Portions cannot be reduced below the {reserved} already reserved."

        if error:
            db.session.rollback()
            flash(error, "danger")
            return render_template(
                "vendor/edit_listing.html",
                listing=listing,
                available_tags=DEFAULT_DIETARY_TAGS,
                selected_tags=selected_tags,
                form_data=request.form,
            )

        listing.title = data["title"]
        listing.description = data["description"]
        listing.total_portions = data["portions"]
        listing.remaining_portions = data["portions"] - reserved
        listing.pickup_location = data["pickup_location"]
        listing.pickup_start = data["pickup_start"]
        listing.pickup_end = data["pickup_end"]
        listing.tags = _resolve_dietary_tags(selected_tags)
        db.session.commit()

        flash("Listing updated successfully!", "success")
        return redirect(url_for("vendor.vendor_listings"))

    # GET: pre-fill the form from the saved listing
    form_data = {
        "title": listing.title,
        "description": listing.description or "",
        "portions": listing.total_portions,
        "pickup_location": listing.pickup_location,
        "pickup_start": listing.pickup_start.strftime("%Y-%m-%dT%H:%M"),
        "pickup_end": listing.pickup_end.strftime("%Y-%m-%dT%H:%M"),
    }
    return render_template(
        "vendor/edit_listing.html",
        listing=listing,
        available_tags=DEFAULT_DIETARY_TAGS,
        selected_tags=[tag.name for tag in listing.tags],
        form_data=form_data,
    )


@vendor_bp.route("/vendor/listings/<int:listing_id>/cancel", methods=["POST"])
@vendor_required
def cancel_listing(listing_id):
    listing = _get_owned_listing(listing_id, lock=True)

    if listing.display_status != "active":
        db.session.rollback()
        flash("This listing can no longer be cancelled.", "danger")
        return redirect(url_for("vendor.vendor_listings"))

    listing.status = "cancelled"

    # Cascade: cancel every active reservation and give its portions back
    for reservation in listing.reservations:
        if reservation.status == "active":
            reservation.status = "cancelled"
            listing.remaining_portions += reservation.portions_reserved

    db.session.commit()

    flash("Listing cancelled. Its active reservations were cancelled too.", "success")
    return redirect(url_for("vendor.vendor_listings"))


@vendor_bp.route("/listings/new", methods=["GET", "POST"])
@vendor_required
def new_listing():
    if request.method == "POST":
        selected_tags = request.form.getlist("dietary_tags")
        data, error = _validate_listing_form(request.form)

        if error:
            flash(error, "danger")
            return render_template(
                "vendor/new_listing.html",
                available_tags=DEFAULT_DIETARY_TAGS,
                selected_tags=selected_tags,
                form_data=request.form,
            )

        # Create new Listing record
        new_item = Listing(
            vendor_id=current_user.id,
            title=data["title"],
            description=data["description"],
            total_portions=data["portions"],
            remaining_portions=data["portions"],
            pickup_location=data["pickup_location"],
            pickup_start=data["pickup_start"],
            pickup_end=data["pickup_end"],
            status="active",
        )

        new_item.tags = _resolve_dietary_tags(selected_tags)
        db.session.add(new_item)
        db.session.commit()

        flash("Listing posted successfully!", "success")
        return redirect(url_for("vendor.vendor_listings"))

    return render_template(
        "vendor/new_listing.html",
        available_tags=DEFAULT_DIETARY_TAGS,
        selected_tags=[],
        form_data={},
    )


def expire_passed_reservations_for_listing(listing, now=None):
    """Transition any active reservations to no-show for a listing whose pickup window ended."""
    if now is None:
        now = datetime.now()

    if now > listing.pickup_end:
        active_reservations = [res for res in listing.reservations if res.status == "active"]
        for res in active_reservations:
            res.status = "no-show"
        db.session.commit()


@vendor_bp.route("/vendor/confirm-pickup", methods=["GET", "POST"])
@vendor_required
def confirm_pickup():
    if request.method == "POST":
        pickup_code = request.form.get("pickup_code", "").strip().upper()

        # Validate pickup code format
        if len(pickup_code) != 6 or not pickup_code.isascii() or not pickup_code.isalnum():
            flash("Pickup code must contain exactly 6 letters or numbers.", "danger")
            return redirect(url_for("vendor.confirm_pickup"))

        # Find reservation by pickup code with eager loaded relationships
        reservation = db.session.execute(
            db.select(Reservation)
            .options(
                selectinload(Reservation.listing),
                selectinload(Reservation.student),
            )
            .filter_by(pickup_code=pickup_code)
            # Lock the reservation row for update to prevent race conditions
            .with_for_update(of=Reservation)
        ).scalar_one_or_none()

        # Check whether the pickup code exists and belongs to the logged-in vendor
        if reservation is None or reservation.listing.vendor_id != current_user.id:
            db.session.rollback()
            flash("Invalid code.", "danger")
            return redirect(url_for("vendor.confirm_pickup"))

        # Verify the reservation is still active
        if reservation.status != "active":
            db.session.rollback()
            flash(
                f"Cannot confirm pickup. Reservation status is '{reservation.status}'.",
                "danger",
            )
            return redirect(url_for("vendor.confirm_pickup"))

        # Check the listing's pickup window
        listing = reservation.listing
        now = datetime.now()

        # Pickup window has not started yet
        if now < listing.pickup_start:
            db.session.rollback()
            flash("The pickup window has not started yet.", "danger")
            return redirect(url_for("vendor.confirm_pickup"))

        # Pickup window has already ended
        if now > listing.pickup_end:
            expire_passed_reservations_for_listing(listing, now=now)
            flash("The pickup window has ended. Reservation marked as no-show.", "danger")
            return redirect(url_for("vendor.confirm_pickup"))

        # Confirm pickup
        reservation.status = "picked up"
        db.session.commit()

        # Display pickup confirmation
        return render_template(
            "vendor/confirm_pickup.html",
            confirmed_reservation=reservation,
        )

    return render_template("vendor/confirm_pickup.html")


@vendor_bp.route("/vendor/dashboard", methods=["GET"])
@vendor_required
# As a vendor, I want an impact dashboard showing portions rescued and no-shows so that I can report results to the sustainability office.

def vendor_dashboard():
    # Retrieve the selected date range from the URL
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    # Convert the start date string into a Python date
    if start_date:
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            flash("Please enter a valid start date.", "danger")
            return redirect(url_for("vendor.vendor_dashboard"))

    # Convert the end date string into a Python date
    if end_date:
        try:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            flash("Please enter a valid end date.", "danger")
            return redirect(url_for("vendor.vendor_dashboard"))

    # Ensure the start date is not after the end date
    if start_date and end_date and start_date > end_date:
        flash("Start date cannot be after end date.", "danger")
        return redirect(url_for("vendor.vendor_dashboard"))

    # Start with listings belonging to the current vendor
    query = db.select(Listing).filter_by(vendor_id=current_user.id)

    # Filter listings by the selected start date
    if start_date:
        query = query.where(db.func.date(Listing.created_at) >= start_date)

    # Filter listings by the selected end date
    if end_date:
        query = query.where(db.func.date(Listing.created_at) <= end_date)

    # Retrieve the filtered listings
    listings = db.session.execute(query.order_by(Listing.created_at.desc())).scalars().all()

    # Calculate listing counts and portions using SQLAlchemy
    total_listings_posted, total_portions_posted = db.session.execute(
        query.with_only_columns(
            db.func.count(Listing.id),
            db.func.coalesce(db.func.sum(Listing.total_portions), 0),
        )
    ).one()

    # Calculate total portions posted
    total_portions_posted = sum(listing.total_portions for listing in listings)

    # Calculate reservation totals using SQLAlchemy
    reservation_totals = db.session.execute(
        db.select(
            Reservation.status,
            db.func.count(Reservation.id),
            db.func.coalesce(db.func.sum(Reservation.portions_reserved), 0),
        )
        .where(Reservation.listing_id.in_(query.with_only_columns(Listing.id)))
        .group_by(Reservation.status)
    ).all()

    # Organize reservation counts and portions by status
    reservation_counts = {status: count for status, count, portions in reservation_totals}
    reservation_portions = {status: portions for status, count, portions in reservation_totals}

    total_portions_picked_up = reservation_portions.get("picked up", 0)
    total_no_show_portions = reservation_portions.get("no-show", 0)
    total_no_show_reservations = reservation_counts.get("no-show", 0)
    total_portions_reserved = sum(
        portions
        for status, portions in reservation_portions.items()
        if status != "cancelled"
    )

    # calculate the no-show rate as percentage
    if total_portions_reserved > 0:
        no_show_rate = (total_no_show_portions / total_portions_reserved) * 100
    else:
        no_show_rate = 0

    return render_template(
        "vendor/dashboard.html",
        listings=listings,
        total_portions_posted=total_portions_posted,
        total_portions_picked_up=total_portions_picked_up,
        total_no_show_portions=total_no_show_portions,
        total_no_show_reservations=total_no_show_reservations,
        no_show_rate=no_show_rate,
        total_listings_posted=total_listings_posted,
    )
