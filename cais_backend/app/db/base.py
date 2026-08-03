from sqlalchemy.ext.declarative import declarative_base

# Create the declarative base for all ORM models.
# This follows SQLAlchemy 2.0 style and is compatible with async usage.
Base = declarative_base()
