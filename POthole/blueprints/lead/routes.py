
from . import bp
from flask import render_template, abort
from flask_login import login_required, current_user

@bp.before_request
def guard():
    if not (current_user.is_authenticated and current_user.role == "lead"):
        abort(403)

@bp.route("/")
@login_required
def dashboard():
    return render_template("lead/dashboard.html")
