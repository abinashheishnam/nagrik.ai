from sqlalchemy import inspect
from app.db.session import engine

def check_columns():
    insp = inspect(engine)
    cols = [c['name'] for c in insp.get_columns('complaints')]
    print("Columns in 'complaints':", cols)

if __name__ == "__main__":
    check_columns()
