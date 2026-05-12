"""הגדרות תוכניות מנוי - features, מגבלות."""
from dataclasses import dataclass
from typing import Literal

from fastapi import Depends, HTTPException, status

from app.auth.deps import current_user
from app.storage import User

PlanName = Literal["free", "pro", "vip"]
PLAN_RANK = {"free": 0, "pro": 1, "vip": 2}


@dataclass(frozen=True)
class PlanLimits:
    name: PlanName
    display_name: str
    watchlist_max: int  # 0 = unlimited
    can_manual_scan: bool
    can_custom_strategy: bool
    can_export: bool
    notifications_history_days: int
    monthly_price_ils: int


PLANS: dict[str, PlanLimits] = {
    "free": PlanLimits(
        name="free",
        display_name="חינם",
        watchlist_max=5,
        can_manual_scan=False,
        can_custom_strategy=False,
        can_export=False,
        notifications_history_days=7,
        monthly_price_ils=0,
    ),
    "pro": PlanLimits(
        name="pro",
        display_name="Pro",
        watchlist_max=50,
        can_manual_scan=True,
        can_custom_strategy=False,
        can_export=True,
        notifications_history_days=30,
        monthly_price_ils=99,
    ),
    "vip": PlanLimits(
        name="vip",
        display_name="VIP",
        watchlist_max=0,  # unlimited
        can_manual_scan=True,
        can_custom_strategy=True,
        can_export=True,
        notifications_history_days=365,
        monthly_price_ils=349,
    ),
}


def limits_for(user: User | None) -> PlanLimits:
    if not user:
        return PLANS["free"]
    return PLANS.get(user.plan, PLANS["free"])


def require_plan(min_plan: PlanName):
    """תלות שמחייבת תוכנית מינימלית. שימוש: dependencies=[Depends(require_plan('pro'))]"""
    required = PLAN_RANK[min_plan]

    def _checker(user: User = Depends(current_user)) -> User:
        user_rank = PLAN_RANK.get(user.plan, 0)
        if user.is_admin:
            return user
        if user_rank < required:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"תכונה זו זמינה למנויי {PLANS[min_plan].display_name} ומעלה",
            )
        return user

    return _checker
