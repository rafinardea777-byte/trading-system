"""נקודות API לאימות - signup, login, me, logout."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import select

from app.auth.deps import current_user
from app.auth.security import create_access_token, hash_password, verify_password
from app.core.config import settings
from app.storage import User, get_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=80)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    plan: str
    is_admin: bool
    created_at: datetime


TokenOut.model_rebuild()


@router.post("/signup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def signup(data: SignupIn):
    if not settings.allow_signup:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="הרשמה סגורה זמנית")

    with get_session() as session:
        existing = session.exec(select(User).where(User.email == data.email.lower())).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="כתובת מייל כבר רשומה")

        user = User(
            email=data.email.lower(),
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            plan="free",
            last_login_at=datetime.utcnow(),
        )
        session.add(user)
        session.flush()
        token = create_access_token(user.id, user.email)
        out_user = UserOut.model_validate(user, from_attributes=True)

    return TokenOut(access_token=token, user=out_user)


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn):
    with get_session() as session:
        user = session.exec(select(User).where(User.email == data.email.lower())).first()
        if not user or not verify_password(data.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="מייל או סיסמה שגויים")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="החשבון מושבת")

        user.last_login_at = datetime.utcnow()
        session.add(user)
        token = create_access_token(user.id, user.email)
        out_user = UserOut.model_validate(user, from_attributes=True)

    return TokenOut(access_token=token, user=out_user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return UserOut.model_validate(user, from_attributes=True)
