"""
Seed script — populates DB with realistic test data.
Run: python seed.py
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.db.session import SessionLocal
from app.modules.auth.model import User
from app.modules.tasks.model import Task
from app.core.security import hash_password

db = SessionLocal()


def seed():
    print("🌱 Seeding database...")
    db.query(Task).delete()
    db.query(User).delete()
    db.commit()

    # ── Users ──────────────────────────────────────────────────────
    users = [
        User(name="Alice Admin", email="admin@test.com",
             hashed_password=hash_password("Admin@123"),
             role="admin", department="IT", experience_years=10, location="Mumbai"),

        User(name="Bob Manager", email="manager@test.com",
             hashed_password=hash_password("Manager@123"),
             role="manager", department="Finance", experience_years=7, location="Delhi"),

        User(name="Carol Finance", email="carol@test.com",
             hashed_password=hash_password("User@123"),
             role="user", department="Finance", experience_years=5, location="Mumbai"),

        User(name="Dave Finance Senior", email="dave@test.com",
             hashed_password=hash_password("User@123"),
             role="user", department="Finance", experience_years=8, location="Delhi"),

        User(name="Eve HR", email="eve@test.com",
             hashed_password=hash_password("User@123"),
             role="user", department="HR", experience_years=4, location="Bangalore"),

        User(name="Frank IT", email="frank@test.com",
             hashed_password=hash_password("User@123"),
             role="user", department="IT", experience_years=6, location="Mumbai"),

        User(name="Grace Ops", email="grace@test.com",
             hashed_password=hash_password("User@123"),
             role="user", department="Operations", experience_years=3, location="Chennai"),

        User(name="Henry Finance Junior", email="henry@test.com",
             hashed_password=hash_password("User@123"),
             role="user", department="Finance", experience_years=1, location="Mumbai"),
    ]
    db.add_all(users)
    db.commit()
    for u in users:
        db.refresh(u)

    admin, manager = users[0], users[1]

    # ── Tasks ──────────────────────────────────────────────────────
    tasks = [
        Task(
            title="Q4 Finance Audit",
            description="Prepare and submit Q4 audit report",
            priority="high",
            assignment_rules={"department": "Finance", "min_experience": 4, "max_active_tasks": 5},
            created_by=admin.id,
            status="todo",
        ),
        Task(
            title="Cloud Cost Optimisation",
            description="Review and reduce cloud infrastructure costs",
            priority="medium",
            assignment_rules={"department": "IT", "min_experience": 3, "location": "Mumbai"},
            created_by=manager.id,
            status="todo",
        ),
        Task(
            title="HR Policy Revamp",
            description="Update leave and remote work policies for 2026",
            priority="low",
            assignment_rules={"department": "HR"},
            created_by=admin.id,
            status="todo",
        ),
        Task(
            title="Operations Process Review",
            description="Review warehouse and logistics workflows",
            priority="medium",
            assignment_rules={"department": "Operations", "max_active_tasks": 3},
            created_by=admin.id,
            status="todo",
        ),
        Task(
            title="Senior Finance Strategy",
            description="Long-term financial planning for 2026-2027",
            priority="high",
            assignment_rules={"department": "Finance", "min_experience": 7, "location": "Delhi"},
            created_by=admin.id,
            status="todo",
        ),
    ]
    db.add_all(tasks)
    db.commit()

    print(f"✅ Seeded {len(users)} users and {len(tasks)} tasks.")
    print()
    print("Test credentials:")
    print("  Admin:   admin@test.com   / Admin@123")
    print("  Manager: manager@test.com / Manager@123")
    print("  User:    carol@test.com   / User@123")
    print()
    print("Note: Run Celery worker to process task assignments.")
    print("  celery -A app.workers.celery_worker.celery_app worker --loglevel=info")


seed()
db.close()