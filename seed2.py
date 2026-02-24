import random
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.modules import User, Project, Organization, Task, TaskStatus, TaskPriority, TaskType, ProjectStatus, ProjectPriority

fake = Faker()

def run_seed():
    db = SessionLocal()
    try:
        print("🌱 Starting massive seed (1000+ records)...")

        # 1. Seed 10 Organizations
        print("Creating Organizations...")
        orgs = []
        for _ in range(10):
            org = Organization(
                name=fake.unique.company(),
                description=fake.catch_phrase(),
                is_active=True
            )
            db.add(org)
            orgs.append(org)
        db.commit()

        # 2. Seed 100 Users (with Rule Engine fields)
        print("Creating 100 Users...")
        depts = ["Finance", "HR", "IT", "Operations", "Trading"]
        locations = ["Mumbai", "London", "New York", "Remote", "Singapore"]
        users = []
        for i in range(100):
            user = User(
                name=fake.name(),
                email=f"user{i}{fake.unique.random_int()}@example.com",
                hashed_password="fake_hashed_password", # In real apps, use pwd_context.hash()
                role=random.choice(["admin", "manager", "user"]),
                department=random.choice(depts),
                experience_years=random.randint(1, 15),
                location=random.choice(locations),
                is_active=True
            )
            db.add(user)
            users.append(user)
        db.commit()

        # 3. Seed 100 Projects
        print("Creating 100 Projects...")
        projects = []
        for _ in range(100):
            start_date = fake.date_between(start_date='-1y', end_date='today')
            project = Project(
                name=f"Project {fake.bs().title()}",
                description=fake.paragraph(),
                organization_id=random.choice(orgs).id,
                start_date=start_date,
                end_date=start_date + timedelta(days=random.randint(30, 180)),
                status=random.choice(list(ProjectStatus)),
                priority=random.choice(list(ProjectPriority)),
                project_owner_id=random.choice(users).id
            )
            # Add random team members (Many-to-Many)
            project.team_members = random.sample(users, k=random.randint(3, 8))
            db.add(project)
            projects.append(project)
        db.commit()

        # 4. Seed 800 Tasks (Totaling 1000+ entries)
        print("Creating 800 Tasks...")
        for _ in range(800):
            proj = random.choice(projects)
            task = Task(
                title=fake.sentence(nb_words=4),
                description=fake.text(),
                task_type=random.choice(list(TaskType)),
                organization_id=proj.organization_id,
                project_id=proj.id,
                status=random.choice(list(TaskStatus)),
                priority=random.choice(list(TaskPriority)),
                created_by=random.choice(users).id,
                assigned_to=random.choice(users).id,
                assignment_rules={
                    "department": random.choice(depts),
                    "min_experience": 4,
                    "location": "Mumbai"
                }
            )
            db.add(task)
        
        db.commit()
        print(f"✅ Success! Seeded {len(orgs)} Orgs, {len(users)} Users, {len(projects)} Projects, and 800 Tasks.")

    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_seed()