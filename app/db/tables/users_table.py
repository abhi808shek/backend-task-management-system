# app/db/create_tables.py
from app.db.base import Base
# from app.modules.tasks.api import Task
from app.modules.projects.api import Project
from app.modules.auth.api import User
from app.db.session import engine

# Create all tables in the database
Base.metadata.create_all(bind=engine)

print("✅ Tables created:", Base.metadata.tables.keys())
