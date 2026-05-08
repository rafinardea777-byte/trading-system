"""FastAPI entrypoint - שרת ה-API + הדשבורד."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

from app.api import news as news_router
from app.api import notifications as notifications_router
from app.auth.router import router as auth_router
from app.api import signals as signals_router
from app.api import stats as stats_router
from app.api import stocks as stocks_router
from app.api import system as system_router
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import limiter
from app.storage import init_db

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    log.info("app_startup", env=settings.app_env, mode=settings.trading_mode)
    if settings.enable_scheduler:
        from app.scheduler.jobs import start_scheduler, stop_scheduler

        start_scheduler()
        try:
            yield
        finally:
            stop_scheduler()
    else:
        yield
    log.info("app_shutdown")


app = FastAPI(
    title="Trading System",
    description="מערכת מאוחדת לסריקת חדשות + סיגנלי שוק",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if settings.public_mode else "/docs",
    redoc_url=None if settings.public_mode else "/redoc",
)

# rate limiting
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "יותר מדי בקשות - נסה שוב בעוד דקה"},
    )


# CORS - ב-public_mode הגבל למקור ספציפי
_origins = ["*"] if not settings.public_mode else [
    o.strip() for o in settings.cors_origins.split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ראוטרים
app.include_router(auth_router)
app.include_router(signals_router.router)
app.include_router(news_router.router)
app.include_router(stats_router.router)
app.include_router(stocks_router.router)
app.include_router(notifications_router.router)
app.include_router(system_router.router)


# הגשה סטטית - הדשבורד והקבצים
WEB_DIR = Path(__file__).resolve().parent / "web"
STATIC_DIR = WEB_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def root():
    """הדשבורד הראשי."""
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "Trading System API", "docs": "/docs"}
