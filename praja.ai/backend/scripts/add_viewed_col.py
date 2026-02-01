import sqlalchemy
from sqlalchemy import text
from app.utils.config import settings

def migrate():
    print(f"Connecting to {settings.DATABASE_URL}...")
    engine = sqlalchemy.create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        print("Checking if column exists...")
        # Check if column exists
        try:
            conn.execute(text("SELECT is_viewed_by_admin FROM complaints LIMIT 1"))
            print("Column 'is_viewed_by_admin' already exists.")
        except Exception:
            print("Column missing. Adding...")
            try:
                conn.execute(text("ALTER TABLE complaints ADD COLUMN is_viewed_by_admin BOOLEAN DEFAULT 0"))
                conn.commit()
                print("Successfully added 'is_viewed_by_admin' column.")
            except Exception as e:
                print(f"Failed to add column: {e}")

if __name__ == "__main__":
    migrate()
