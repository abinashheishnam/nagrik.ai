from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import Admin
from app.auth.security import hash_password

DEFAULT_USER = "admin"
DEFAULT_PASS = "Admin@123"

def main():
    db: Session = SessionLocal()
    try:
        exists = db.query(Admin).filter(Admin.username == DEFAULT_USER).first()
        if exists:
            print("✅ Admin already exists.")
            return
        admin = Admin(username=DEFAULT_USER, password_hash=hash_password(DEFAULT_PASS))
        db.add(admin)
        db.commit()
        print("✅ Admin created:")
        print("   username:", DEFAULT_USER)
        print("   password:", DEFAULT_PASS)
    finally:
        db.close()

if __name__ == "__main__":
    main()
