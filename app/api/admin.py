"""נקודות API ל-admin בלבד - ניהול משתמשים."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import select

from app.auth.deps import require_admin_user
from app.auth.plans import PLAN_RANK
from app.storage import User, UserWatchlist, get_session

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AdminUserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    plan: str
    is_admin: bool
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    watchlist_count: int


class UserPatch(BaseModel):
    plan: Optional[str] = Field(default=None)
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


@router.get("/users", response_model=list[AdminUserOut])
def list_users(_: User = Depends(require_admin_user)):
    with get_session() as session:
        users = list(session.exec(select(User).order_by(User.created_at.desc())))
        out = []
        for u in users:
            wc = len(list(session.exec(
                select(UserWatchlist).where(UserWatchlist.user_id == u.id)
            )))
            out.append(AdminUserOut(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                plan=u.plan,
                is_admin=u.is_admin,
                is_active=u.is_active,
                created_at=u.created_at,
                last_login_at=u.last_login_at,
                watchlist_count=wc,
            ))
        return out


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(user_id: int, data: UserPatch, admin: User = Depends(require_admin_user)):
    with get_session() as session:
        u = session.get(User, user_id)
        if not u:
            raise HTTPException(status_code=404, detail="משתמש לא נמצא")
        if data.plan is not None:
            if data.plan not in PLAN_RANK:
                raise HTTPException(status_code=400, detail="תוכנית לא תקינה")
            u.plan = data.plan
        if data.is_active is not None:
            u.is_active = data.is_active
        if data.is_admin is not None:
            # מונע ניתוק עצמי
            if u.id == admin.id and data.is_admin is False:
                raise HTTPException(status_code=400, detail="לא ניתן להסיר admin מעצמך")
            u.is_admin = data.is_admin
        session.add(u)
        session.flush()
        wc = len(list(session.exec(
            select(UserWatchlist).where(UserWatchlist.user_id == u.id)
        )))
        return AdminUserOut(
            id=u.id, email=u.email, full_name=u.full_name, plan=u.plan,
            is_admin=u.is_admin, is_active=u.is_active,
            created_at=u.created_at, last_login_at=u.last_login_at,
            watchlist_count=wc,
        )


@router.delete("/users/{user_id}")
def delete_user(user_id: int, admin: User = Depends(require_admin_user)):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="לא ניתן למחוק את עצמך")
    with get_session() as session:
        u = session.get(User, user_id)
        if not u:
            raise HTTPException(status_code=404, detail="משתמש לא נמצא")
        # מחק watchlist קודם
        for wl in session.exec(select(UserWatchlist).where(UserWatchlist.user_id == user_id)):
            session.delete(wl)
        session.delete(u)
    return {"ok": True}


class AdminStatsOut(BaseModel):
    total_users: int
    active_users: int
    free_users: int
    pro_users: int
    vip_users: int
    total_revenue_ils: int
    new_today: int
    new_week: int


@router.get("/stats", response_model=AdminStatsOut)
def admin_stats(_: User = Depends(require_admin_user)):
    from datetime import timedelta
    from app.auth.plans import PLANS

    with get_session() as session:
        users = list(session.exec(select(User)))
        active = [u for u in users if u.is_active]
        free = [u for u in users if u.plan == "free"]
        pro = [u for u in users if u.plan == "pro"]
        vip = [u for u in users if u.plan == "vip"]

        revenue = sum(PLANS[u.plan].monthly_price_ils for u in active if u.plan in PLANS)

        now = datetime.utcnow()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        new_today = [u for u in users if u.created_at >= day_ago]
        new_week = [u for u in users if u.created_at >= week_ago]

        return AdminStatsOut(
            total_users=len(users),
            active_users=len(active),
            free_users=len(free),
            pro_users=len(pro),
            vip_users=len(vip),
            total_revenue_ils=revenue,
            new_today=len(new_today),
            new_week=len(new_week),
        )
