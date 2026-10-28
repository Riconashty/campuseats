# Authentication routes
from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash
from campuseats.extensions import db
from campuseats.models.user import User
from sqlalchemy.exc import IntegrityError

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

        # Check if the email is already registered
        existing_user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
        if existing_user:
            flash("Email is already registered. Please log in or use a different email.", "danger")
            return render_template("register.html")

        # Hash password before storing it
        password_hash = generate_password_hash(password)

        # Create new User object
        new_user = User(
            name=name,
            email=email,
            password_hash=password_hash,
            role=role
        )

        #save the new user to PostgreSQL database
        try:
            db.session.add(new_user)
            db.session.commit()

        #If PostgreSQL rejects the record because of a database constraint, Python cathces the error. 
        except IntegrityError: 
            db.session.rollback()
            flash("An error occurred while creating the account. Please try again.", "danger")
            return render_template("register.html")

        #confirm successful registration and redirect to login page
        flash("Account created successfully!", "success")
        return redirect(url_for("auth.register"))  # Redirect to login page after successful registration

    return render_template("register.html")