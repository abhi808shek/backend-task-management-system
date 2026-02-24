from app.db.base import Base
from app.db.session import engine
# from app.modules.tasks.api import Task
from app.modules.projects.api import Project
from app.modules.auth.api import User

def create_schema():
    print("Connecting to task_db and creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Success! Tables created.")

if __name__ == "__main__":
    create_schema()
