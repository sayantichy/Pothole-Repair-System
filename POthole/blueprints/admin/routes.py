from . import bp
from flask import render_template, abort, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func
from extensions import db
from models import (
    User, District, Crew, CrewMembership,
    Pothole, WorkOrder, PotholeReport
)

def _admin_only():
    return current_user.is_authenticated and current_user.role == "admin"

@bp.before_request
def guard():
    if not _admin_only():
        abort(403)

@bp.route("/")
@login_required
def dashboard():
    stats = {
        "users": User.query.count(),
        "districts": District.query.count(),
        "crews": Crew.query.count(),
        "potholes": Pothole.query.count(),
        "work_orders": WorkOrder.query.count(),
    }
    latest_reported = (Pothole.query
                       .order_by(Pothole.created_at.desc())
                       .limit(8).all())

    # crews with active work (planned or in_progress)
    active_status = ["planned", "in_progress"]
    crew_rows = []
    for c in Crew.query.order_by(Crew.name.asc()).all():
        count = (WorkOrder.query
                 .filter(WorkOrder.crew_id == c.id, WorkOrder.status.in_(active_status))
                 .count())
        crew_rows.append({"crew": c, "active": count})

    return render_template("admin/dashboard.html",
                           stats=stats,
                           latest_reported=latest_reported,
                           crew_rows=crew_rows)

# ----- Users (roles) -----
@bp.get("/users")
@login_required
def users():
    return render_template("admin/users.html", users=User.query.order_by(User.id.desc()).all())

@bp.post("/users/role")
@login_required
def set_role():
    uid = int(request.form["user_id"])
    role = request.form["role"]
    u = User.query.get_or_404(uid)
    u.role = role
    db.session.commit()
    flash("Role updated.", "success")
    return redirect(url_for("admin.users"))

# ----- Users overview -----
@bp.get("/users-overview")
@login_required
def users_overview():
    reporters = (db.session.query(User)
                 .join(PotholeReport, PotholeReport.reporter_id == User.id)
                 .filter(User.role == "citizen")
                 .distinct()
                 .order_by(User.id.desc())
                 .all())
    staff_and_leads = User.query.filter(User.role.in_(["staff", "lead"])) \
                                .order_by(User.id.desc()).all()
    crews = Crew.query.order_by(Crew.id.asc()).all()
    return render_template("admin/users_overview.html",
                           reporters=reporters,
                           staff_and_leads=staff_and_leads,
                           crews=crews)

# ----- Crews mgmt -----
@bp.get("/crews")
@login_required
def crews():
    crews = Crew.query.order_by(Crew.id.desc()).all()
    users = User.query.order_by(User.name.asc()).all()
    return render_template("admin/crews.html", crews=crews, users=users)

@bp.post("/crews/create")
@login_required
def create_crew():
    name = request.form.get("name", "").strip()
    number = request.form.get("crew_number", "").strip()
    people_count = int(request.form.get("people_count", 0) or 0)
    if not name or not number:
        flash("Name and crew number are required.", "warning")
        return redirect(url_for("admin.crews"))
    db.session.add(Crew(name=name, crew_number=number, people_count=people_count))
    db.session.commit()
    flash("Crew created.", "success")
    return redirect(url_for("admin.crews"))

@bp.post("/crews/set-lead")
@login_required
def set_crew_lead():
    crew_id = int(request.form["crew_id"])
    user_id = int(request.form["user_id"])
    crew = Crew.query.get_or_404(crew_id)
    user = User.query.get_or_404(user_id)
    crew.lead_user_id = user.id
    if user.role != "lead":
        user.role = "lead"
    db.session.commit()
    flash("Crew lead assigned.", "success")
    return redirect(url_for("admin.crews"))

@bp.post("/crews/add-member")
@login_required
def add_crew_member():
    crew_id = int(request.form["crew_id"])
    user_id = int(request.form["user_id"])
    crew = Crew.query.get_or_404(crew_id)
    user = User.query.get_or_404(user_id)
    if not CrewMembership.query.filter_by(crew_id=crew.id, user_id=user.id).first():
        db.session.add(CrewMembership(crew_id=crew.id, user_id=user.id))
    if user.role == "citizen":
        user.role = "staff"
    db.session.commit()
    flash("Member added to crew.", "success")
    return redirect(url_for("admin.crews"))

@bp.post("/crews/remove-member")
@login_required
def remove_crew_member():
    crew_id = int(request.form["crew_id"])
    user_id = int(request.form["user_id"])
    mem = CrewMembership.query.filter_by(crew_id=crew_id, user_id=user_id).first_or_404()
    db.session.delete(mem)
    db.session.commit()
    flash("Member removed.", "success")
    return redirect(url_for("admin.crews"))

# ----- Potholes + Assign crew + Update status -----
@bp.get("/potholes")
@login_required
def potholes():
    status = (request.args.get("status") or "").strip()
    district_id = request.args.get("district_id")
    q_str = (request.args.get("q") or "").strip()

    q = Pothole.query
    if status:
        q = q.filter(Pothole.status == status)
    if district_id:
        try:
            q = q.filter(Pothole.district_id == int(district_id))
        except ValueError:
            pass
    if q_str:
        q = q.filter(Pothole.street_address.ilike(f"%{q_str}%"))

    potholes = q.order_by(Pothole.created_at.desc()).all()
    crews = Crew.query.order_by(Crew.name.asc()).all()
    districts = District.query.order_by(District.name.asc()).all()

    rows = []
    for p in potholes:
        wo = p.work_orders.order_by(WorkOrder.updated_at.desc()).first()
        rows.append({"p": p, "wo": wo})

    return render_template("admin/potholes.html",
                           rows=rows, crews=crews, districts=districts,
                           selected_status=status, selected_district=district_id, q=q_str)

@bp.post("/potholes/assign")
@login_required
def assign_crew():
    pothole_id = int(request.form["pothole_id"])
    crew_id = int(request.form["crew_id"])
    pothole = Pothole.query.get_or_404(pothole_id)
    crew = Crew.query.get_or_404(crew_id)
    wo = WorkOrder(pothole_id=pothole.id, crew_id=crew.id, status="planned")
    db.session.add(wo)
    pothole.status = "in_progress"
    db.session.commit()
    flash(f"Crew '{crew.name}' assigned. WO #{wo.id} created.", "success")
    return redirect(url_for("admin.potholes"))

@bp.post("/potholes/status")
@login_required
def set_pothole_status():
    pothole_id = int(request.form["pothole_id"])
    status = request.form["status"].strip()
    p = Pothole.query.get_or_404(pothole_id)
    p.status = status
    db.session.commit()
    flash("Pothole status updated.", "success")
    return redirect(url_for("admin.potholes"))

# ----- Work Orders (who is doing which work) -----
@bp.get("/work-orders")
@login_required
def work_orders():
    crew_id = request.args.get("crew_id")
    status = (request.args.get("status") or "").strip()
    q = WorkOrder.query
    if crew_id:
        try:
            q = q.filter(WorkOrder.crew_id == int(crew_id))
        except ValueError:
            pass
    if status:
        q = q.filter(WorkOrder.status == status)
    orders = q.order_by(WorkOrder.updated_at.desc()).limit(500).all()
    crews = Crew.query.order_by(Crew.name.asc()).all()
    return render_template("admin/work_orders.html", orders=orders, crews=crews,
                           selected_status=status, selected_crew=crew_id)

@bp.post("/work-orders/status")
@login_required
def set_work_order_status():
    wo_id = int(request.form["wo_id"])
    status = request.form["status"].strip()
    wo = WorkOrder.query.get_or_404(wo_id)
    wo.status = status
    db.session.commit()
    flash("Work order status updated.", "success")
    return redirect(url_for("admin.work_orders"))
