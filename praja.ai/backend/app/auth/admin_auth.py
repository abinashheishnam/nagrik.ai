import os

ADMIN_ID = "admin"
ADMIN_PASSWORD = "admin123"

def verify_admin(id: str, password: str):
    return id == ADMIN_ID and password == ADMIN_PASSWORD
