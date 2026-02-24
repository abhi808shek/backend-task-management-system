import random
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine
from app.db.base import Base
# Ensure all models are imported so relationships work
from app.modules import User, Project, Organization, Task, TaskStatus, TaskPriority, TaskType, ProjectStatus, ProjectPriority

fake = Faker()

def run_seed():
    db = SessionLocal()
    try:
        print("🚀 Starting Database Seed...")

        # 1. Create 5 Organizations (Multi-tenancy support)
        print("Seeding Organizations...")
        orgs = []
        for _ in range(5):
            org = Organization(
                name=fake.unique.company(),
                description=fake.catch_phrase(),
                is_active=True
            )
            db.add(org)
            orgs.append(org)
        db.flush() # Flush to get IDs for foreign keys

        # 2. Seed 10 Users
        print("Seeding 10 Users...")
        users = []
        departments = ["Finance", "HR", "IT", "Operations"]
        locations = ["Mumbai", "Bangalore", "London", "Remote"]
        
        for i in range(10):
            user = User(
                name=fake.name(),
                email=fake.unique.email(),
                hashed_password="hashed_password_example",
                role=random.choice(["admin", "manager", "user"]),
                department=random.choice(departments),
                experience_years=random.randint(1, 10),
                location=random.choice(locations),
                is_active=True
            )
            db.add(user)
            users.append(user)
        db.flush()

        # 3. Seed 100 Projects
        print("Seeding 100 Projects...")
        projects = []
        for _ in range(100):
            start_date = fake.date_between(start_date='-30d', end_date='today')
            project = Project(
                name=f"Project {fake.catch_phrase()}",
                description=fake.text(max_nb_chars=200),
                organization_id=random.choice(orgs).id,
                start_date=start_date,
                end_date=start_date + timedelta(days=random.randint(30, 90)),
                status=random.choice(list(ProjectStatus)),
                priority=random.choice(list(ProjectPriority)),
                project_owner_id=random.choice(users).id
            )
            # Add random team members (Many-to-Many)
            project.team_members = random.sample(users, k=random.randint(2, 5))
            db.add(project)
            projects.append(project)
        db.flush()

        # 4. Seed 100 Tasks
        print("Seeding 100 Tasks...")
        tasks_pool = []
        for _ in range(100):
            proj = random.choice(projects)
            task = Task(
                title=fake.sentence(nb_words=4),
                description=fake.paragraph(),
                task_type=random.choice(list(TaskType)),
                organization_id=proj.organization_id,
                project_id=proj.id,
                status=random.choice(list(TaskStatus)),
                priority=random.choice(list(TaskPriority)),
                created_by=random.choice(users).id,
                assigned_to=random.choice(users).id,
                assignment_rules={
                    "department": random.choice(departments),
                    "min_experience": 4,
                    "location": "Mumbai"
                }
            )
            db.add(task)
            tasks_pool.append(task)
        
        db.flush()

        # 5. Seed Task Subtasks (Self-referential Many-to-Many)
        print("Connecting random subtasks...")
        for _ in range(30):
            parent = random.choice(tasks_pool)
            subtask = random.choice(tasks_pool)
            if parent.id != subtask.id:
                parent.subtasks.append(subtask)

        db.commit()
        print("Success! Database seeded with 10 Orgs, 10 Users, 100 Projects, and 100 Tasks.")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_seed()