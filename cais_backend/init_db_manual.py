from app.core.database import engine
from app.db.models import Base

def init():
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ All tables created successfully!")

if __name__ == "__main__":
    init()
