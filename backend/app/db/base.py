from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Future models are imported here so Alembic can discover them via Base.metadata.