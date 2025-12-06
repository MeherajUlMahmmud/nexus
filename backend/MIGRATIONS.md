# Database Migrations with Alembic

This project uses [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations.

## Quick Reference

```bash
# Activate virtual environment first
source venv/bin/activate

# Create a new migration after model changes
alembic revision --autogenerate -m "description_of_changes"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View current migration status
alembic current

# View migration history
alembic history
```

## Workflow

### 1. Making Model Changes

Edit your models in `app/models/`. For example:

```python
# app/models/user.py
class User(BaseModel):
    __tablename__ = "users"
    
    email = Column(String, unique=True, nullable=False)
    new_field = Column(String, nullable=True)  # New field added
```

### 2. Generate Migration

```bash
alembic revision --autogenerate -m "add_new_field_to_users"
```

This creates a new file in `alembic/versions/` with the detected changes.

### 3. Review Migration

Always review the generated migration file before applying:

```python
# alembic/versions/xxxx_add_new_field_to_users.py
def upgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('new_field', sa.String(), nullable=True))

def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('new_field')
```

### 4. Apply Migration

```bash
alembic upgrade head
```

## Common Commands

| Command | Description |
|---------|-------------|
| `alembic upgrade head` | Apply all pending migrations |
| `alembic downgrade -1` | Rollback one migration |
| `alembic downgrade base` | Rollback all migrations |
| `alembic current` | Show current revision |
| `alembic history` | Show migration history |
| `alembic revision -m "msg"` | Create empty migration |
| `alembic revision --autogenerate -m "msg"` | Auto-generate migration |

## SQLite Notes

This project uses SQLite with batch mode enabled (`render_as_batch=True`). This is required because SQLite has limited `ALTER TABLE` support. Alembic handles this by:

1. Creating a new table with the desired schema
2. Copying data from the old table
3. Dropping the old table
4. Renaming the new table

## Adding New Models

When adding new models, ensure they are imported in `alembic/env.py`:

```python
# alembic/env.py
from app.models.your_new_model import YourNewModel
```

Models are already imported via `app.models`, but explicit imports ensure detection.

## Troubleshooting

### Migration not detecting changes

- Ensure the model is imported in `alembic/env.py`
- Check that the model inherits from `Base` (via `BaseModel`)

### "Target database is not up to date"

```bash
alembic upgrade head
```

### Reset migrations (development only)

```bash
# Delete all migrations
rm alembic/versions/*.py

# Drop alembic_version table
sqlite3 chat_app.db "DROP TABLE IF EXISTS alembic_version;"

# Create fresh migration
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

