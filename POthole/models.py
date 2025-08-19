from datetime import datetime
from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class District(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)

class User(UserMixin, TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, index=True)
    phone = db.Column(db.String(32))
    role = db.Column(db.String(20), default="citizen")  # citizen/staff/lead/admin
    password_hash = db.Column(db.String(255))

    def set_password(self, pw): self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)

    @property
    def wallet_balance(self):
        from sqlalchemy.sql import func, case
        total = db.session.query(
            func.coalesce(func.sum(case((WalletTransaction.type=="credit", WalletTransaction.amount), else_=-WalletTransaction.amount)), 0)
        ).filter(WalletTransaction.user_id==self.id).scalar()
        return float(total or 0)

class Crew(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    crew_number = db.Column(db.String(20), unique=True)
    people_count = db.Column(db.Integer)
    # NEW: crew lead
    lead_user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    lead = db.relationship("User", foreign_keys=[lead_user_id])

class CrewMembership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crew_id = db.Column(db.Integer, db.ForeignKey("crew.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    role = db.Column(db.String(20), default="member")  # member
    crew = db.relationship("Crew", backref=db.backref("members", cascade="all, delete-orphan"))
    user = db.relationship("User")

# (Team/TeamMembership can stay if you already added them; they won’t break anything.)

class Pothole(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(16), unique=True, index=True)
    street_address = db.Column(db.String(255), nullable=False)
    address_norm = db.Column(db.String(255), index=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    size_1_10 = db.Column(db.Integer, nullable=False)
    location_type = db.Column(db.String(30))  # middle/curb/edge
    district_id = db.Column(db.Integer, db.ForeignKey("district.id"))
    district = db.relationship("District")
    priority = db.Column(db.String(10))       # Low/Medium/High
    status = db.Column(db.String(20), default="reported")
    reporter_name = db.Column(db.String(120))
    reporter_email = db.Column(db.String(120))
    reporter_phone = db.Column(db.String(32))

    work_orders = db.relationship("WorkOrder", backref="pothole", lazy="dynamic", cascade="all, delete-orphan")
    photos = db.relationship("Photo", backref="pothole", lazy="dynamic", cascade="all, delete-orphan")
    reports = db.relationship("PotholeReport", backref="pothole", lazy="dynamic", cascade="all, delete-orphan")

class WorkOrder(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pothole_id = db.Column(db.Integer, db.ForeignKey("pothole.id"), nullable=False)
    crew_id = db.Column(db.Integer, db.ForeignKey("crew.id"))
    crew = db.relationship("Crew")
    start_at = db.Column(db.DateTime)
    end_at = db.Column(db.DateTime)
    hours_applied = db.Column(db.Float, default=0)
    people_used = db.Column(db.Integer, default=0)
    filler_material_kg = db.Column(db.Float, default=0)
    material_cost = db.Column(db.Float, default=0)
    equipment_cost = db.Column(db.Float, default=0)
    labor_cost = db.Column(db.Float, default=0)
    total_cost = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default="planned")
    notes = db.Column(db.Text)

class Photo(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pothole_id = db.Column(db.Integer, db.ForeignKey("pothole.id"), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    filename = db.Column(db.String(255), nullable=False)
    file_hash = db.Column(db.String(64), index=True)

class PotholeReport(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pothole_id = db.Column(db.Integer, db.ForeignKey("pothole.id"), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    is_duplicate = db.Column(db.Boolean, default=False)
    reward_granted = db.Column(db.Boolean, default=False)
    photo_count = db.Column(db.Integer, default=0)

class WalletTransaction(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), default="credit")  # credit|debit
    description = db.Column(db.String(255))
    ref_report_id = db.Column(db.Integer, db.ForeignKey("pothole_report.id"))

class Issue(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pothole_id = db.Column(db.Integer, db.ForeignKey("pothole.id"))
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    title = db.Column(db.String(200))
    body = db.Column(db.Text)
    status = db.Column(db.String(20), default="open")
