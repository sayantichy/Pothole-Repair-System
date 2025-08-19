from . import bp
from flask import render_template, abort
from flask_login import login_required, current_user
from models import PotholeReport, Pothole, WalletTransaction, Photo

@bp.before_request
def guard():
    if not (current_user.is_authenticated and current_user.role == "citizen"):
        abort(403)

@bp.route("/dashboard")
@login_required
def dashboard():
    reports = (PotholeReport.query
               .filter_by(reporter_id=current_user.id)
               .order_by(PotholeReport.created_at.desc())
               .all())

    items = []
    for r in reports:
        p = Pothole.query.get(r.pothole_id)
        if not p:
            continue
        photos = (Photo.query
                  .filter_by(pothole_id=p.id, reporter_id=current_user.id)
                  .order_by(Photo.created_at.desc())
                  .all())
        items.append({"report": r, "pothole": p, "photos": photos})

    latest = items[:6]

    total = len(items)
    reported = sum(1 for it in items if it["pothole"].status == "reported")
    in_prog = sum(1 for it in items if it["pothole"].status == "in_progress")
    repaired = sum(1 for it in items if it["pothole"].status == "repaired")
    stats = dict(total=total, reported=reported, in_progress=in_prog, repaired=repaired)

    txs = (WalletTransaction.query
           .filter_by(user_id=current_user.id)
           .order_by(WalletTransaction.created_at.desc())
           .limit(50).all())

    return render_template(
        "user/reporter_dashboard.html",
        wallet=current_user.wallet_balance,
        stats=stats,
        latest=latest,
        items=items,
        txs=txs
    )
