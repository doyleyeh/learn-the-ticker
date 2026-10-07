from alembic import context
from sqlalchemy import create_engine
from backend.app.db import Base

config = context.config
connection = config.attributes.get("connection")
if connection is not None:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
else:
    raise RuntimeError("Migrations must be invoked by the application with its private database connection")
