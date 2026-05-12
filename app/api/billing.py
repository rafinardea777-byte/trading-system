"""תשתית billing - מוכן ל-Stripe. ב-test mode עד שמוסיפים keys."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.auth.deps import current_user
from app.auth.plans import PLANS
from app.core.config import settings
from app.core.logging import get_logger
from app.storage import User, get_session

router = APIRouter(prefix="/api/billing", tags=["billing"])
log = get_logger(__name__)


class CheckoutIn(BaseModel):
    plan: str  # "pro" | "vip"


class CheckoutOut(BaseModel):
    url: Optional[str] = None
    mode: str  # "stripe" | "manual" | "disabled"
    message: Optional[str] = None


def _stripe_configured() -> bool:
    return bool(settings.stripe_secret_key) and (
        bool(settings.stripe_price_id_pro) or bool(settings.stripe_price_id_vip)
    )


@router.get("/status")
def billing_status():
    """מאפשר לקליינט לדעת אם Stripe מוגדר ולהציג מסך מתאים."""
    return {
        "stripe_enabled": _stripe_configured(),
        "publishable_key": settings.stripe_publishable_key if _stripe_configured() else None,
        "contact_email": settings.contact_email,
    }


@router.post("/checkout", response_model=CheckoutOut)
def create_checkout(data: CheckoutIn, user: User = Depends(current_user)):
    """יוצר checkout session ב-Stripe אם מוגדר. אחרת מחזיר manual mode."""
    if data.plan not in ("pro", "vip"):
        raise HTTPException(status_code=400, detail="תוכנית לא תקינה")

    if not _stripe_configured():
        return CheckoutOut(
            mode="manual",
            message=f"לרכישה - שלח מייל ל-{settings.contact_email} עם השם והתוכנית המבוקשת ({data.plan})",
        )

    price_id = settings.stripe_price_id_pro if data.plan == "pro" else settings.stripe_price_id_vip
    if not price_id:
        raise HTTPException(status_code=500, detail="תוכנית לא מוגדרת ב-Stripe")

    try:
        import stripe

        stripe.api_key = settings.stripe_secret_key

        # יצירת customer אם אין
        customer_id = user.stripe_customer_id
        if not customer_id:
            customer = stripe.Customer.create(email=user.email, name=user.full_name or user.email)
            customer_id = customer.id
            with get_session() as session:
                u = session.get(User, user.id)
                u.stripe_customer_id = customer_id
                session.add(u)

        session_url = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            customer=customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{settings.public_base_url}?upgrade=success",
            cancel_url=f"{settings.public_base_url}?upgrade=cancel",
            metadata={"user_id": str(user.id), "plan": data.plan},
        ).url

        return CheckoutOut(url=session_url, mode="stripe")
    except ImportError:
        return CheckoutOut(mode="manual", message="ספריית stripe לא מותקנת. צור קשר ידני.")
    except Exception as e:
        log.error("stripe_checkout_failed", error=str(e))
        raise HTTPException(status_code=500, detail="יצירת תשלום נכשלה. נסה שוב או צור קשר.")


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """מטפל באירועי subscription. נדרש Stripe webhook secret."""
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="webhook לא מוגדר")

    try:
        import stripe
    except ImportError:
        raise HTTPException(status_code=500, detail="stripe not installed")

    sig = request.headers.get("stripe-signature", "")
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.stripe_webhook_secret)
    except Exception as e:
        log.warning("stripe_webhook_invalid", error=str(e))
        raise HTTPException(status_code=400, detail="invalid signature")

    etype = event["type"]
    obj = event["data"]["object"]

    if etype == "checkout.session.completed":
        user_id = int((obj.get("metadata") or {}).get("user_id", "0"))
        plan = (obj.get("metadata") or {}).get("plan", "pro")
        sub_id = obj.get("subscription")
        with get_session() as session:
            u = session.get(User, user_id)
            if u:
                u.plan = plan
                u.stripe_subscription_id = sub_id
                u.subscription_status = "active"
                session.add(u)
                log.info("user_upgraded", user_id=user_id, plan=plan)

    elif etype == "customer.subscription.deleted":
        sub_id = obj.get("id")
        with get_session() as session:
            from sqlmodel import select
            u = session.exec(select(User).where(User.stripe_subscription_id == sub_id)).first()
            if u:
                u.plan = "free"
                u.subscription_status = "canceled"
                session.add(u)

    elif etype == "customer.subscription.updated":
        sub_id = obj.get("id")
        sub_status = obj.get("status")
        with get_session() as session:
            from sqlmodel import select
            u = session.exec(select(User).where(User.stripe_subscription_id == sub_id)).first()
            if u:
                u.subscription_status = sub_status
                if sub_status in ("canceled", "past_due", "unpaid"):
                    u.plan = "free"
                session.add(u)

    return {"received": True}
