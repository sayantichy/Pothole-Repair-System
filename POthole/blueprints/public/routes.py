from . import bp
from flask import render_template, request, redirect, url_for, flash, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db
from models import Pothole, District, WorkOrder, Crew, Photo, PotholeReport
from services.rules import compute_priority
from services.geo import normalize_address, haversine_m
from services.wallet import credit_reward
import os, uuid, hashlib

def _allowed(filename):
    ext = filename.rsplit(".",1)[-1].lower()
    return ext in current_app.config.get("ALLOWED_EXTENSIONS", set())

@bp.route("/")
def home():
    # Stats
    total = Pothole.query.count()
    reported = Pothole.query.filter_by(status="reported").count()
    in_prog = Pothole.query.filter_by(status="in_progress").count()
    repaired = Pothole.query.filter_by(status="repaired").count()
    latest = Pothole.query.order_by(Pothole.created_at.desc()).limit(6).all()
    return render_template("public/home.html",
                           stats=dict(total=total, reported=reported, in_progress=in_prog, repaired=repaired),
                           latest=latest)

@bp.post("/track")
def track_lookup():
    tid = (request.form.get("tracking_id","") or "").strip().upper()
    if not tid:
        flash("Enter a tracking ID.", "warning")
        return redirect(url_for("public.home"))
    p = Pothole.query.filter_by(public_id=tid).first()
    if not p:
        flash("Tracking ID not found.", "warning")
        return redirect(url_for("public.home"))
    return redirect(url_for("public.track", public_id=p.public_id))

@bp.route("/report", methods=["GET", "POST"])
@login_required
def report():
    if current_user.role != "citizen":
        flash("Only citizen accounts can submit reports.", "warning")
        return redirect(url_for("public.home"))
    if request.method == "POST":
        addr = request.form["street_address"].strip()
        size = int(request.form["size_1_10"])
        location_type = request.form.get("location_type", "middle")
        lat = request.form.get("latitude"); lon = request.form.get("longitude")
        lat = float(lat) if lat else None; lon = float(lon) if lon else None
        district = District.query.first()
        addr_norm = normalize_address(addr)
        candidate = Pothole.query.filter_by(address_norm=addr_norm).first()
        if not candidate and (lat is not None and lon is not None):
            for p in Pothole.query.order_by(Pothole.created_at.desc()).limit(200):
                d = haversine_m(lat, lon, p.latitude, p.longitude)
                if d is not None and d <= 30:
                    candidate = p; break
        if candidate:
            pothole = candidate; is_dup = True
        else:
            pothole = Pothole(
                public_id=uuid.uuid4().hex[:8].upper(),
                street_address=addr, address_norm=addr_norm,
                latitude=lat, longitude=lon,
                size_1_10=size, location_type=location_type,
                district=district, priority=compute_priority(size),
                reporter_name=current_user.name, reporter_email=current_user.email, reporter_phone=current_user.phone,
            )
            db.session.add(pothole); db.session.flush()
            is_dup = False

        files = request.files.getlist("photos"); saved = 0
        upload_dir = current_app.config["UPLOAD_FOLDER"]; os.makedirs(upload_dir, exist_ok=True)
        for f in files:
            if not f or not f.filename: continue
            if not _allowed(f.filename): flash("Only JPG/PNG allowed.", "warning"); continue
            fname = secure_filename(f.filename); unique = f"{uuid.uuid4().hex}_{fname}"
            path = os.path.join(upload_dir, unique); f.save(path)
            with open(path, "rb") as fh: h = hashlib.sha1(fh.read()).hexdigest()
            exists = Photo.query.filter_by(pothole_id=pothole.id, file_hash=h).first()
            if exists: continue
            db.session.add(Photo(pothole_id=pothole.id, reporter_id=current_user.id, filename=unique, file_hash=h)); saved += 1

        report = PotholeReport(pothole_id=pothole.id, reporter_id=current_user.id, is_duplicate=is_dup, photo_count=saved)
        db.session.add(report); db.session.flush()
        if not is_dup: credit_reward(current_user.id, report.id)
        db.session.commit()

        flash(("This pothole was already reported. " if is_dup else "Report submitted. +20 Tk credited. ")
              + f"Tracking ID: {pothole.public_id}", "success" if not is_dup else "warning")
        return redirect(url_for("public.track", public_id=pothole.public_id))
    return render_template("public/report.html")

@bp.route("/track/<public_id>")
def track(public_id):
    pothole = Pothole.query.filter_by(public_id=public_id).first_or_404()
    work_orders = pothole.work_orders.order_by(WorkOrder.updated_at.desc()).all()
    return render_template("public/track.html", pothole=pothole, work_orders=work_orders)

@bp.route("/uploads/<path:filename>")
def uploaded_file(filename):
    # Only serve allowed image types
    try:
        ext = filename.rsplit(".", 1)[-1].lower()
    except Exception:
        ext = ""
    if ext not in current_app.config.get("ALLOWED_EXTENSIONS", {"jpg","jpeg","png"}):
        # hide anything not an allowed image
        return "", 404
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(upload_dir, filename)
