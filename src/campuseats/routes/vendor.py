from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from campuseats.extensions import db
from campuseats.models.listing import DEFAULT_DIETARY_TAGS, DietaryTag, Listing
from campuseats.routes.role_guards import vendor_required

vendor_bp = Blueprint("vendor", __name__)


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
    return render_template("vendor/listings.html", listings=listings)


@vendor_bp.route("/listings/new", methods=["GET", "POST"])
@vendor_required
def new_listing():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        portions_raw = request.form.get("portions", "").strip()
        pickup_location = request.form.get("pickup_location", "").strip()
        pickup_start_raw = request.form.get("pickup_start", "").strip()
        pickup_end_raw = request.form.get("pickup_end", "").strip()
        selected_tags = request.form.getlist("dietary_tags")

        # Validate required fields
        required_fields = {
            "Title": title,
            "Portions": portions_raw,
            "Pickup Location": pickup_location,
            "Pickup Start": pickup_start_raw,
            "Pickup End": pickup_end_raw,
        }

        for field_name, value in required_fields.items():
            if not value:
                flash(f"Please complete all required fields. Missing: {field_name}.", "danger")
                return render_template(
                    "vendor/new_listing.html",
                    available_tags=DEFAULT_DIETARY_TAGS,
                    selected_tags=selected_tags,
                    form_data=request.form,
                )

        # Validate portions integer range between 1 and 100
        try:
            portions = int(portions_raw)
            if portions < 1 or portions > 100:
                raise ValueError
        except ValueError:
            flash("Portions must be an integer between 1 and 100.", "danger")
            return render_template(
                "vendor/new_listing.html",
                available_tags=DEFAULT_DIETARY_TAGS,
                selected_tags=selected_tags,
                form_data=request.form,
            )

        # Parse pickup window start and end datetimes
        try:
            pickup_start = datetime.fromisoformat(pickup_start_raw)
            pickup_end = datetime.fromisoformat(pickup_end_raw)
        except ValueError:
            flash("Please provide valid dates and times for the pickup window.", "danger")
            return render_template(
                "vendor/new_listing.html",
                available_tags=DEFAULT_DIETARY_TAGS,
                selected_tags=selected_tags,
                form_data=request.form,
            )

        now = datetime.now()

        # Pickup end cannot be in the past
        if pickup_end < now:
            flash("Pickup end time cannot be in the past.", "danger")
            return render_template(
                "vendor/new_listing.html",
                available_tags=DEFAULT_DIETARY_TAGS,
                selected_tags=selected_tags,
                form_data=request.form,
            )

        # Pickup end cannot be before or equal to pickup start
        if pickup_end <= pickup_start:
            flash("Pickup end time must be after pickup start time.", "danger")
            return render_template(
                "vendor/new_listing.html",
                available_tags=DEFAULT_DIETARY_TAGS,
                selected_tags=selected_tags,
                form_data=request.form,
            )

        # Create new Listing record
        new_item = Listing(
            vendor_id=current_user.id,
            title=title,
            description=description if description else None,
            total_portions=portions,
            remaining_portions=portions,
            pickup_location=pickup_location,
            pickup_start=pickup_start,
            pickup_end=pickup_end,
            status="active",
        )

        # Resolve validated dietary tags
        tags_to_attach = []
        for tag_name in selected_tags:
            tag_name_clean = tag_name.strip().lower()
            if tag_name_clean in DEFAULT_DIETARY_TAGS:
                tag = db.session.execute(
                    db.select(DietaryTag).filter_by(name=tag_name_clean)
                ).scalar_one_or_none()
                if not tag:
                    tag = DietaryTag(name=tag_name_clean)
                    db.session.add(tag)
                tags_to_attach.append(tag)

        new_item.tags = tags_to_attach
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
