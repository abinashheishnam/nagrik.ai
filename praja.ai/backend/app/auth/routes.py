from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User, Admin
from app.auth.security import hash_password, verify_password, create_access_token
from app.schemas.auth import UserSignup, UserLogin, AdminLogin, AdminSignup, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/user/signup", response_model=TokenOut)
def user_signup(payload: UserSignup, db: Session = Depends(get_db)):
    if db.query(User).filter(User.phone == payload.phone).first():
        raise HTTPException(status_code=400, detail="Phone already registered")
    if payload.email and db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        full_name=payload.full_name,
        phone=payload.phone,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(sub=str(user.id), role="user")
    return TokenOut(access_token=token, role="user")

@router.post("/user/login", response_model=TokenOut)
def user_login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter((User.phone == payload.identifier) | (User.email == payload.identifier)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(sub=str(user.id), role="user")
    return TokenOut(access_token=token, role="user")

@router.post("/admin/signup", response_model=TokenOut)
def admin_signup(payload: AdminSignup, db: Session = Depends(get_db)):
    # simple security check
    if payload.secret_key != "admin_secret": 
        raise HTTPException(status_code=403, detail="Invalid admin secret")
    
    if db.query(Admin).filter(Admin.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Admin username taken")

    admin = Admin(
        username=payload.username,
        password_hash=hash_password(payload.password)
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    token = create_access_token(sub=str(admin.id), role="admin")
    return TokenOut(access_token=token, role="admin")

@router.post("/admin/login", response_model=TokenOut)
def admin_login(payload: AdminLogin, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.username == payload.username).first()
    if not admin or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")

    token = create_access_token(sub=str(admin.id), role="admin")
    return TokenOut(access_token=token, role="admin")

from app.auth.dependencies import get_current_user
from app.schemas.auth import UserOut

@router.get("/me", response_model=UserOut)
def get_my_profile(user=Depends(get_current_user)):
    return user
