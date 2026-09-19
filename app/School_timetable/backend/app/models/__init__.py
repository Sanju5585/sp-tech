from app.database import Base

# Re-export so Alembic and create_all pick up every model.
from app.models.entities import *  # noqa: F403
