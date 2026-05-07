"""CLI - הרצה ידנית של סריקות, יצוא דוחות, init DB."""
import argparse
import sys

from app.core.logging import get_logger
from app.storage import init_db

log = get_logger(__name__)


def cmd_init_db(args):
    init_db()
    print("[OK] DB initialized")


def cmd_scan_news(args):
    init_db()
    from app.scanners.news import run_news_scan

    result = run_news_scan(hours_back=args.hours)
    print(f"[OK] news scan done: {result}")

    if args.report:
        from app.enrichment.summarizer import create_summary
        from app.reports import generate_html_report, generate_markdown_report
        from app.storage import get_session
        from app.storage.repository import get_news

        with get_session() as session:
            items = [
                {
                    "source": n.source, "author": n.author, "text": n.text,
                    "url": n.url, "created_at": n.published_at.isoformat() if n.published_at else "",
                    "hebrew_translation": n.hebrew_translation,
                    "hebrew_explanation": n.hebrew_explanation,
                }
                for n in get_news(session, hours_back=args.hours, limit=200)
            ]
        summary = create_summary(items)
        md = generate_markdown_report(items, summary)
        html = generate_html_report(items, summary)
        print(f"[OK] markdown: {md}")
        print(f"[OK] html: {html}")


def cmd_scan_market(args):
    init_db()
    from app.scanners.market import run_market_scan

    result = run_market_scan(
        include_sp500=args.sp500,
        send_alerts=not args.no_alerts,
        max_symbols=args.max,
    )
    print(f"[OK] market scan done: {result}")


def cmd_serve(args):
    """הפעלת שרת FastAPI."""
    import uvicorn

    from app.core.config import settings

    uvicorn.run(
        "app.main:app",
        host=args.host or settings.api_host,
        port=args.port or settings.api_port,
        reload=args.reload,
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="trading-system", description="Trading System CLI")
    sub = p.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init-db", help="יצירת בסיס נתונים")
    p_init.set_defaults(func=cmd_init_db)

    p_news = sub.add_parser("scan-news", help="סריקת חדשות")
    p_news.add_argument("--hours", type=int, default=24)
    p_news.add_argument("--report", action="store_true", help="גם הפק דוחות MD/HTML")
    p_news.set_defaults(func=cmd_scan_news)

    p_mkt = sub.add_parser("scan-market", help="סריקת שוק טכנית")
    p_mkt.add_argument("--sp500", action="store_true", help="כולל S&P 500 (איטי)")
    p_mkt.add_argument("--max", type=int, default=None, help="מקסימום מניות לסריקה")
    p_mkt.add_argument("--no-alerts", action="store_true", help="ללא שליחת התראות")
    p_mkt.set_defaults(func=cmd_scan_market)

    p_srv = sub.add_parser("serve", help="הפעלת שרת FastAPI + דשבורד")
    p_srv.add_argument("--host", default=None)
    p_srv.add_argument("--port", type=int, default=None)
    p_srv.add_argument("--reload", action="store_true")
    p_srv.set_defaults(func=cmd_serve)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
        return 0
    except KeyboardInterrupt:
        print("\n[!] interrupted")
        return 130
    except Exception as e:
        log.error("cli_failed", error=str(e))
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
