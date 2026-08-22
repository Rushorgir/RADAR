"""
Database Seeding Script for RADAR/OrbitGuard

Generates realistic synthetic data for testing the backend API and frontend dashboard.
Run this script from the project root:
    python scripts/seed_database.py
"""

import sys
import os
import uuid
import random
from datetime import datetime, timedelta

# Add project root to path so we can import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.backend.db.connection import engine, Base, SessionLocal
from src.backend.db.models import TLEModel, ConjunctionEventModel


def seed_database():
    print("Initializing Database...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Clear existing data
        print("Clearing old data...")
        db.query(ConjunctionEventModel).delete()
        db.query(TLEModel).delete()
        db.commit()

        # Generate TLEs
        print("Seeding TLE records...")
        object_types = ["PAYLOAD", "DEBRIS", "ROCKET_BODY"]
        tles = []
        for i in range(1, 51):
            obj_id = f"{25000 + i}"
            tle = TLEModel(
                object_id=obj_id,
                object_name=f"SAT-{obj_id}" if i % 3 == 0 else f"DEBRIS-{obj_id}",
                object_type=random.choice(object_types),
                line1=f"1 {obj_id}U 98067A   23315.50000000  .00000000  00000-0  00000-0 0  9999",
                line2=f"2 {obj_id}  51.6400 300.0000 0005000 100.0000 250.0000 15.50000000 12345",
                epoch=datetime.utcnow() - timedelta(days=random.random()),
                inclination_deg=random.uniform(45.0, 98.0),
                eccentricity=random.uniform(0.0001, 0.05),
                mean_motion_rev_day=random.uniform(14.0, 16.0)
            )
            tles.append(tle)
        
        db.bulk_save_objects(tles)
        db.commit()

        # Generate Conjunction Events
        print("Seeding Conjunction Events...")
        events = []
        now = datetime.utcnow()
        
        risk_categories = ["HIGH"] * 5 + ["MEDIUM"] * 10 + ["LOW"] * 15
        
        for i in range(30):
            tca = now + timedelta(hours=random.uniform(1.0, 72.0))
            risk_cat = risk_categories[i]
            
            if risk_cat == "HIGH":
                miss_dist = random.uniform(0.05, 1.0)
                pc = random.uniform(1e-4, 1e-2)
                ml_score = random.uniform(0.75, 0.99)
            elif risk_cat == "MEDIUM":
                miss_dist = random.uniform(1.0, 3.0)
                pc = random.uniform(1e-6, 1e-4)
                ml_score = random.uniform(0.4, 0.75)
            else:
                miss_dist = random.uniform(3.0, 8.0)
                pc = random.uniform(1e-8, 1e-6)
                ml_score = random.uniform(0.01, 0.4)
                
            event = ConjunctionEventModel(
                event_id=str(uuid.uuid4()),
                primary_id=f"{25000 + random.randint(1, 25)}",
                secondary_id=f"{25000 + random.randint(26, 50)}",
                tca=tca,
                miss_distance_km=miss_dist,
                relative_velocity_km_s=random.uniform(7.0, 15.0),
                pc=pc,
                pc_method="FOSTER_2D" if random.random() > 0.1 else "MONTE_CARLO",
                primary_object_type="PAYLOAD",
                secondary_object_type=random.choice(["DEBRIS", "ROCKET_BODY"]),
                ml_risk_score=ml_score,
                risk_category=risk_cat,
                shap_top_features=[
                    {"feature": "miss_distance", "impact": round(random.uniform(-0.5, 0.5), 3)},
                    {"feature": "relative_velocity", "impact": round(random.uniform(-0.3, 0.3), 3)},
                    {"feature": "pc", "impact": round(random.uniform(-0.4, 0.4), 3)}
                ]
            )
            
            if risk_cat == "HIGH" and random.random() > 0.3:
                event.maneuver_delta_v_m_s = random.uniform(0.05, 0.5)
                event.maneuver_burn_direction = "ALONG_TRACK"
                event.maneuver_new_miss_distance_km = miss_dist + random.uniform(2.0, 5.0)
                event.maneuver_fuel_cost_estimate_kg = random.uniform(0.01, 0.1)
                
            events.append(event)

        db.bulk_save_objects(events)
        db.commit()
        print("Database seeded successfully!")
        
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
