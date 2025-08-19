from . import bp
from flask import jsonify, request
from extensions import db
from models import Pothole
from services.rules import compute_priority
import uuid

@bp.route("/status")
def status():
    return jsonify({"ok": True, "service": "PHTRS"})

@bp.post("/potholes")
def api_create_pothole():
    data = request.get_json(force=True)
    ph = Pothole(
        public_id=uuid.uuid4().hex[:8].upper(),
        street_address=data["street_address"],
        size_1_10=int(data["size_1_10"]),
        location_type=data.get("location_type", "middle"),
        priority=compute_priority(int(data["size_1_10"]))
    )
    db.session.add(ph)
    db.session.commit()
    return jsonify({"public_id": ph.public_id, "id": ph.id})
