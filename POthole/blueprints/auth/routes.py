from . import bp
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import or_, func
from models import User
from extensions import db

def _post_login_redirect(user: User):
    if user.role == "admin":
        return url_for("admin.dashboard")
    if user.role in ("staff", "lead"):
        return url_for("staff.dashboard")
    if user.role == "citizen":
        return url_for("user.dashboard")
    return url_for("public.home")

@bp.route("/login", methods=["GET","POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_post_login_redirect(current_user))

    if request.method == "POST":
        ident = (request.form.get("email") or request.form.get("username") or "").strip()
        pwd = request.form.get("password") or ""
        remember = bool(request.form.get("remember"))

        if not ident or not pwd:
            flash("Please enter your email/username and password.", "warning")
            return redirect(url_for("auth.login"))

        user = (User.query
                .filter(or_(func.lower(User.email)==ident.lower(),
                            func.lower(User.name)==ident.lower()))
                .first())

        if not user or not user.check_password(pwd):
            flash("Invalid credentials.", "danger")
            return redirect(url_for("auth.login"))

        login_user(user, remember=remember)
        flash(f"Welcome back, {user.name}!", "success")
        return redirect(_post_login_redirect(user))

    return render_template("auth/login.html")

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("public.home"))


from sqlalchemy import func

@bp.route("/register", methods=["GET","POST"])
def register():
    if current_user.is_authenticated:
        # already logged in → send to their area
        try:
            return redirect(_post_login_redirect(current_user))
        except Exception:
            return redirect(url_for("public.home"))

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        phone = (request.form.get("phone") or "").strip()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""

        if not name or not email or not password:
            flash("Please fill name, email and password.", "warning")
            return redirect(url_for("auth.register"))
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.register"))
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "warning")
            return redirect(url_for("auth.register"))

        # email uniqueness (case-insensitive)
        existing = User.query.filter(func.lower(User.email) == email).first()
        if existing:
            flash("An account with that email already exists. Please login.", "warning")
            return redirect(url_for("auth.login"))

        u = User(name=name, email=email, role="citizen")
        if hasattr(u, "phone") and phone:
            u.phone = phone
        u.set_password(password)
        db.session.add(u)
        db.session.commit()

        login_user(u)
        flash("Welcome! Your account has been created.", "success")
        return redirect(url_for("user.dashboard"))

    return render_template("auth/register.html")
