# Authentication routes
from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from campuseats.extensions import db
from campuseats.models.user import User
from sqlalchemy.exc import IntegrityError
from flask_login import login_user, logout_user, login_required, current_user

auth_bp = Blueprint("auth", __name__)


# Registration page
@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "")

        # Validate required fields and identify missing information
        # Creates a dictionary.
        required_fields = {"Name": name, "Email": email, "Password": password, "Role": role}

        # checks each field.
        for field_name, value in required_fields.items():
            if not value:
                flash(f"Please complete all required fields. Missing: {field_name}.", "danger")
                return render_template("register.html")

        # Validate password length
        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
            return render_template("register.html")

        # Validate account type
        if role not in ["student", "vendor"]:
            flash("Please select a valid account type.", "danger")
            return render_template("register.html")

        # Check if the email is already registered
        existing_user = db.session.execute(
            db.select(User).filter_by(email=email)
        ).scalar_one_or_none()
        if existing_user:
            flash("An account with that email already exists.", "danger")
            return render_template("register.html")

        # Hash password before storing it
        password_hash = generate_password_hash(password)

        # Create new User object
        new_user = User(name=name, email=email, password_hash=password_hash, role=role)

        # save the new user to PostgreSQL database
        try:
            db.session.add(new_user)
            db.session.commit()

        # If PostgreSQL rejects the record because of a database constraint, Python cathces the error.
        except IntegrityError:
            db.session.rollback()
            flash("An error occurred while creating the account. Please try again.", "danger")
            return render_template("register.html")

        # confirm successful registration and redirect to login page
        flash("Account created successfully!", "success")
        return redirect(
            url_for("auth.login")
        )  # Redirect to login page after successful registration

    return render_template("register.html")


# Login page
@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    # Redirect users who are already logged in
    if current_user.is_authenticated:
        if current_user.role == "student":
            return redirect("/listings")
        elif current_user.role == "vendor":
            return redirect("/vendor/listings")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # Validate required fields and identify missing information
        required_fields = {"Email": email, "Password": password}

        for field_name, value in required_fields.items():
            if not value:
                flash(f"Please complete all required fields. Missing: {field_name}.", "danger")
                return render_template("auth/login.html")

        # Search database for user with the provided email
        user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()

        # Check if user exists and password is correct
        if user is None or not check_password_hash(user.password_hash, password):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html")

        # Verify that the user has a valid role
        if user.role not in ["student", "vendor"]:
            flash("Unable to log in with this account.", "danger")
            return render_template("auth/login.html")

        # Log in user after successful authentication
        login_user(user)
        # Redirect user depending on their role
        if user.role == "student":
            return redirect("/listings")

        elif user.role == "vendor":
            return redirect("/vendor/listings")

    return render_template("auth/login.html")


# Logout route
@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("auth.login"))
