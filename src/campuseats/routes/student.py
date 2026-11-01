from flask import Blueprint, render_template

from campuseats.routes.role_guards import student_required

student_bp = Blueprint("student", __name__)


@student_bp.get("/listings")
@student_required
def listings():
    # TODO: query active listings once the Listing model (SCRUM-26) is merged.
    return render_template("student/listings.html", listings=[])
