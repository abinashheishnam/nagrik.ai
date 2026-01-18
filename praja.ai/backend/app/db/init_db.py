from app.db.session import Base, engine
from app.db import models  # noqa: F401 (needed to register models)

def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ MySQL tables created successfully.")

if __name__ == "__main__":
    init_db()
