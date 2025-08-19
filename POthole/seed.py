from app import app
from extensions import db
from models import District, Crew

with app.app_context():
    if not District.query.first():
        db.session.add_all([
            District(name="Central", code="CEN"),
            District(name="North", code="NOR"),
        ])
    if not Crew.query.first():
        db.session.add_all([
            Crew(name="Alpha Crew", crew_number="A-01", people_count=4),
            Crew(name="Bravo Crew", crew_number="B-12", people_count=3),
        ])
    db.session.commit()
    print("Seeded Districts & Crews.")
