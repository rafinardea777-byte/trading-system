"""נקודות API לאימות - signup, login, me, password reset, email verify."""
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import select

from app.auth.deps import current_user
from app.auth.security import create_access_token, hash_password, verify_password
from app.core.config import settings
from app.core.email import (
    reset_password_email,
    send_email,
    verify_email_email,
    welcome_email,
)
from app.core.logging import get_logger
from app.storage import User, get_session

router = APIRouter(prefix="/api/auth", tags=["auth"])
log = get_logger(__name__)

RESET_TOKEN_TTL_MINUTES = 30
VERIFY_TOKEN_TTL_HOURS = 48


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=80)
    accept_terms: bool = True


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
    email_verified: bool = False
    daily_digest_enabled: bool = False
    created_at: datetime


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UpdateProfileIn(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=80)


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


TokenOut.model_rebuild()


def _send_welcome(email: str, name: str | None) -> None:
    msg = welcome_email(name or "")
    send_email(email, msg["subject"], msg["html_body"])


def _send_reset(email: str, token: str) -> None:
    link = f"{settings.public_base_url}#reset-password={token}"
    msg = reset_password_email(link)
    send_email(email, msg["subject"], msg["html_body"])


def _send_verify(email: str, token: str) -> None:
    link = f"{settings.public_base_url}#verify-email={token}"
    msg = verify_email_email(link)
    send_email(email, msg["subject"], msg["html_body"])


@router.post("/signup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def signup(data: SignupIn, background: BackgroundTasks):
    if not settings.allow_signup:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="הרשמה סגורה זמנית")
    if not data.accept_terms:
        raise HTTPException(status_code=400, detail="חובה לאשר את תנאי השימוש")

    with get_session() as session:
        existing = session.exec(select(User).where(User.email == data.email.lower())).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="כתובת מייל כבר רשומה")

        verify_token = secrets.token_urlsafe(32)
        user = User(
            email=data.email.lower(),
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            plan="free",
            last_login_at=datetime.utcnow(),
            email_verified=False,
            email_verify_token=verify_token,
            email_verify_expires=datetime.utcnow() + timedelta(hours=VERIFY_TOKEN_TTL_HOURS),
            accepted_terms_at=datetime.utcnow(),
        )
        session.add(user)
        session.flush()
        uid = user.id
        token = create_access_token(uid, user.email)
        out_user = UserOut.model_validate(user, from_attributes=True)

    # שליחת מיילים ברקע - לא חוסם את ההרשמה אם המייל נכשל
    background.add_task(_send_welcome, data.email, data.full_name)
    background.add_task(_send_verify, data.email, verify_token)

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


@router.patch("/me")
def update_profile(data: UpdateProfileIn, user: User = Depends(current_user)):
    with get_session() as session:
        u = session.get(User, user.id)
        if data.full_name is not None:
            u.full_name = data.full_name
        session.add(u)
        return UserOut.model_validate(u, from_attributes=True)


@router.post("/change-password")
def change_password(data: ChangePasswordIn, user: User = Depends(current_user)):
    with get_session() as session:
        u = session.get(User, user.id)
        if not verify_password(data.current_password, u.password_hash):
            raise HTTPException(status_code=401, detail="סיסמה נוכחית שגויה")
        u.password_hash = hash_password(data.new_password)
        session.add(u)
    return {"ok": True}


@router.delete("/me")
def delete_account(user: User = Depends(current_user)):
    """מחיקת חשבון - מוחק את ה-User + watchlist + notifications שלו."""
    from sqlmodel import delete as sql_delete
    from app.storage import Notification, UserWatchlist
    with get_session() as session:
        session.exec(sql_delete(UserWatchlist).where(UserWatchlist.user_id == user.id))
        session.exec(sql_delete(Notification).where(Notification.user_id == user.id))
        u = session.get(User, user.id)
        if u:
            session.delete(u)
    return {"ok": True, "deleted": True}


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordIn, background: BackgroundTasks):
    """תמיד מחזיר ok - לא מגלים אם מייל קיים (anti-enumeration)."""
    email = data.email.lower()
    with get_session() as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expires = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)
            session.add(user)
            background.add_task(_send_reset, email, token)
    return {"ok": True, "message": "אם הכתובת רשומה - יישלח אליה מייל עם קישור איפוס"}


@router.post("/reset-password")
def reset_password(data: ResetPasswordIn):
    with get_session() as session:
        user = session.exec(select(User).where(User.reset_token == data.token)).first()
        if not user or not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
            raise HTTPException(status_code=400, detail="קישור לא תקף או פג תוקפו")
        user.password_hash = hash_password(data.new_password)
        user.reset_token = None
        user.reset_token_expires = None
        session.add(user)
    return {"ok": True, "message": "הסיסמה אופסה. אפשר להתחבר עם הסיסמה החדשה."}


@router.post("/verify-email")
def verify_email(token: str):
    with get_session() as session:
        user = session.exec(select(User).where(User.email_verify_token == token)).first()
        if not user or not user.email_verify_expires or user.email_verify_expires < datetime.utcnow():
            raise HTTPException(status_code=400, detail="קישור אימות לא תקף או פג תוקפו")
        user.email_verified = True
        user.email_verify_token = None
        user.email_verify_expires = None
        session.add(user)
    return {"ok": True, "message": "המייל אומת בהצלחה"}


@router.post("/resend-verification")
def resend_verification(background: BackgroundTasks, user: User = Depends(current_user)):
    if user.email_verified:
        return {"ok": True, "message": "המייל כבר אומת"}
    with get_session() as session:
        u = session.get(User, user.id)
        token = secrets.token_urlsafe(32)
        u.email_verify_token = token
        u.email_verify_expires = datetime.utcnow() + timedelta(hours=VERIFY_TOKEN_TTL_HOURS)
        session.add(u)
    background.add_task(_send_verify, user.email, token)
    return {"ok": True, "message": "מייל אימות נשלח שוב"}
