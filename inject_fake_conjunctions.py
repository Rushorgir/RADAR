import sys; sys.path.insert(0, '.')
import uuid
import random
from datetime import datetime, timezone, timedelta
from src.backend.db.connection import SessionLocal
from src.backend.db.models import TLEModel, ConjunctionEventModel

db = SessionLocal()

# Find some active payloads and debris
payloads = db.query(TLEModel).filter(TLEModel.dataset_name == 'default', TLEModel.object_type == 'PAYLOAD').limit(10).all()
debris = db.query(TLEModel).filter(TLEModel.dataset_name == 'default', TLEModel.object_type == 'DEBRIS').limit(10).all()

if not payloads or not debris:
    print("Not enough objects to inject.")
    sys.exit(0)

# Delete existing fake ones if any
fake_events = db.query(ConjunctionEventModel).filter(ConjunctionEventModel.pc_method == "MOCK_HACKATHON").all()
for f in fake_events:
    db.delete(f)
db.commit()

now = datetime.now(timezone.utc)
fake_events = []

for i in range(5):
    p = random.choice(payloads)
    d = random.choice(debris)
    
    tca = now + timedelta(hours=random.uniform(2, 48))
    miss_distance = random.uniform(0.1, 0.9)
    pc = random.uniform(0.0001, 0.05)
    rel_vel = random.uniform(10.0, 15.0)
    risk_score = random.uniform(0.85, 0.99)
    
    event = ConjunctionEventModel(
        dataset_name="default",
        event_id=str(uuid.uuid4()),
        primary_id=p.object_id,
        secondary_id=d.object_id,
        tca=tca,
        miss_distance_km=miss_distance,
        relative_velocity_km_s=rel_vel,
        pc=pc,
        pc_method="MOCK_HACKATHON",
        primary_object_type=p.object_type,
        secondary_object_type=d.object_type,
        ml_risk_score=risk_score,
        risk_category="CRITICAL",
        maneuver_delta_v_m_s=random.uniform(0.01, 0.1),
        maneuver_burn_direction="Anti-Velocity",
        maneuver_new_miss_distance_km=miss_distance + random.uniform(2.0, 5.0)
    )
    db.add(event)
    fake_events.append(event)

db.commit()
print(f"Injected {len(fake_events)} high-risk conjunctions involving debris.")
