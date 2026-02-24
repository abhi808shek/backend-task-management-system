# app/db/tables/check_users_table.py
from sqlalchemy import inspect
from app.db.session import engine

# Create an inspector object
inspector = inspect(engine)

# List all tables
tables = inspector.get_table_names()
print("Tables in DB:", tables)

# Check if 'users' table exists
if 'users' in tables:
    print("\nColumns in 'users' table:")
    columns = inspector.get_columns('users')
    for col in columns:
        print(f" - {col['name']} ({col['type']}) | "
              f"Nullable: {col['nullable']} | "
              f"Default: {col['default']}")
    
    # Show primary keys
    pks = inspector.get_pk_constraint('users')
    print("\nPrimary Key(s):", pks.get('constrained_columns'))

    # Show unique constraints
    uniques = inspector.get_unique_constraints('users')
    if uniques:
        print("\nUnique Constraints:")
        for u in uniques:
            print(" -", u.get('column_names'))
    else:
        print("\nNo unique constraints found")

else:
    print("❌ 'users' table does not exist")
