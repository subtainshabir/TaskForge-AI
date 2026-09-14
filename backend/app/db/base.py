from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Models register themselves on Base.metadata via app/models/__init__.py,
# which alembic/env.py imports for autogenerate/migration support.