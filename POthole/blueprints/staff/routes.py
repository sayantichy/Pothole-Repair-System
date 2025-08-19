from . import bp
from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from extensions import db
from models import Pothole, WorkOrder, Crew
from datetime import datetime

@bp.before_request
def guard():
    if not current_user.is_authenticated:
        abort(403)
    if current_user.role not in ("staff", "lead"):
        abort(403)

@bp.route("/")
@login_required
def dashboard():
    q = Pothole.query.order_by(Pothole.created_at.desc()).limit(200).all()
    return render_template("staff/dashboard.html", potholes=q)

@bp.route("/pothole/<int:pid>", methods=["GET", "POST"])
@login_required
def edit_pothole(pid):
    pothole = Pothole.query.get_or_404(pid)
    crews = Crew.query.all()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create_wo":
            crew_id = int(request.form["crew_id"])
            wo = WorkOrder(pothole_id=pothole.id, crew_id=crew_id, status="planned", start_at=datetime.utcnow())
            db.session.add(wo)
            pothole.status = "in_progress"
            db.session.commit()
            flash("Work order created.", "success")
        elif action == "update_wo":
            wo_id = int(request.form["wo_id"])
            wo = WorkOrder.query.get_or_404(wo_id)
            wo.hours_applied = float(request.form.get("hours_applied", 0) or 0)
            wo.people_used = int(request.form.get("people_used", 0) or 0)
            wo.filler_material_kg = float(request.form.get("filler_material_kg", 0) or 0)
            wo.material_cost = float(request.form.get("material_cost", 0) or 0)
            wo.equipment_cost = float(request.form.get("equipment_cost", 0) or 0)
            wo.labor_cost = wo.hours_applied * max(wo.people_used, 1) * 30
            wo.total_cost = wo.labor_cost + wo.material_cost + wo.equipment_cost
            wo.status = request.form.get("wo_status", "in_progress")
            if wo.status == "completed":
                pothole.status = "repaired"
                wo.end_at = datetime.utcnow()
            db.session.commit()
            flash("Work order updated.", "success")
        return redirect(url_for("staff.edit_pothole", pid=pothole.id))
    work_orders = pothole.work_orders.order_by(WorkOrder.updated_at.desc()).all()
    return render_template("staff/edit_pothole.html", pothole=pothole, work_orders=work_orders, crews=crews)
