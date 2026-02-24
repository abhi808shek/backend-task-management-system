

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None


def upgrade():
    # ── USERS TABLE ───────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, server_default="Unknown"),
        sa.Column("email", sa.String(100), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("department", sa.String(50), nullable=True),
        sa.Column("experience_years", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("location", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Unique constraint
    op.create_index("uq_users_email", "users", ["email"], unique=True)

    # Single-column indexes (rule engine filters)
    op.create_index("ix_users_department", "users", ["department"])
    op.create_index("ix_users_location", "users", ["location"])
    op.create_index("ix_users_is_active", "users", ["is_active"])
    op.create_index("ix_users_role", "users", ["role"])

    # Composite index — covers 80% of rule engine queries in one index
    op.create_index(
        "ix_users_dept_exp_active",
        "users",
        ["department", "experience_years", "is_active"],
    )

    # ── TASKS TABLE ───────────────────────────────────────────────
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="todo"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "assignment_rules",
            postgresql.JSONB(),  # JSONB > JSON: indexed, compressed, faster reads
            nullable=False,
            server_default="{}",
        ),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assigned_to", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Single-column indexes
    op.create_index("ix_tasks_assigned_to", "tasks", ["assigned_to"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_priority", "tasks", ["priority"])
    op.create_index("ix_tasks_is_active", "tasks", ["is_active"])
    op.create_index("ix_tasks_created_by", "tasks", ["created_by"])

    # PRIMARY composite index — powers GET /my-eligible-tasks
    # Covers the FULL WHERE clause: assigned_to + is_active + status
    op.create_index(
        "ix_tasks_assigned_active_status",
        "tasks",
        ["assigned_to", "is_active", "status"],
    )

    # Composite for COUNT queries in rule engine
    op.create_index(
        "ix_tasks_assigned_status_active",
        "tasks",
        ["assigned_to", "status", "is_active"],
    )

    # PARTIAL index — only indexes unassigned active tasks
    # Powers retry_unassigned_tasks beat task efficiently
    op.execute("""
        CREATE INDEX ix_tasks_unassigned_active
        ON tasks (is_active, created_at)
        WHERE assigned_to IS NULL AND is_active = true
    """)

    # JSONB GIN index — enables fast rule lookups on assignment_rules field
    # Allows queries like: WHERE assignment_rules @> '{"department": "Finance"}'
    op.execute("""
        CREATE INDEX ix_tasks_assignment_rules_gin
        ON tasks USING GIN (assignment_rules)
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_tasks_assignment_rules_gin")
    op.execute("DROP INDEX IF EXISTS ix_tasks_unassigned_active")
    op.drop_index("ix_tasks_assigned_status_active", "tasks")
    op.drop_index("ix_tasks_assigned_active_status", "tasks")
    op.drop_index("ix_tasks_created_by", "tasks")
    op.drop_index("ix_tasks_is_active", "tasks")
    op.drop_index("ix_tasks_priority", "tasks")
    op.drop_index("ix_tasks_status", "tasks")
    op.drop_index("ix_tasks_assigned_to", "tasks")
    op.drop_table("tasks")

    op.drop_index("ix_users_dept_exp_active", "users")
    op.drop_index("ix_users_role", "users")
    op.drop_index("ix_users_is_active", "users")
    op.drop_index("ix_users_location", "users")
    op.drop_index("ix_users_department", "users")
    op.drop_index("uq_users_email", "users")
    op.drop_table("users")