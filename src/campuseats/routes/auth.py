# Authentication routes
from flask import Blueprint, render_template, request, flash
from werkzeug.security import generate_password_hash

auth_bp = Blueprint("auth", __name__)


# Registration page
@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "")

        # Validate that all required fields are provided
        if not all([name, email, password, role]):
            flash("Please complete all required fields.", "danger")
            return render_template("register.html")

        # Validate password length
        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
            return render_template("register.html")

        # Validate account type
        if role not in ["student", "vendor"]:
            flash("Please select a valid account type.", "danger")
            return render_template("register.html")

        # Hash password before storing it
        password_hash = generate_password_hash(password)

        # TODO: Validate remaining information and save user to PostgreSQL

    return render_template("register.html")