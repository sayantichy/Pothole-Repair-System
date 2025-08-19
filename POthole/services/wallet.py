from extensions import db
from models import WalletTransaction

def credit_reward(user_id: int, report_id: int, amount: float = 20.0, description: str = "Unique pothole report reward"):
    tx = WalletTransaction(user_id=user_id, amount=amount, type="credit", description=description, ref_report_id=report_id)
    db.session.add(tx)
