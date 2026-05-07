"""סורק X (Twitter) - דורש Bearer Token."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.scanners.news.accounts import ALL_ACCOUNTS

log = get_logger(__name__)


def _client() -> Optional[object]:
    if not settings.use_x_api:
        return None
    try:
        import tweepy

        return tweepy.Client(bearer_token=settings.x_bearer_token, wait_on_rate_limit=True)
    except ImportError:
        log.warning("tweepy_not_installed")
        return None


def fetch_tweets(
    hours_back: int = 24,
    max_per_user: int = 20,
    max_total: int = 500,
) -> list[dict]:
    client = _client()
    if not client:
        return []

    start_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    start_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    out: list[dict] = []
    seen: set[str] = set()

    for handle in ALL_ACCOUNTS:
        if len(out) >= max_total:
            break
        try:
            user_resp = client.get_user(username=handle)
            if not user_resp.data:
                continue
            user_id = user_resp.data.id

            resp = client.get_users_tweets(
                id=user_id,
                max_results=min(max_per_user, max_total - len(out)),
                start_time=start_str,
                tweet_fields=["created_at", "author_id", "public_metrics"],
                user_fields=["username"],
                expansions=["author_id"],
            )
            if not resp.data:
                continue

            users_by_id = {u.id: u for u in (resp.includes.get("users") or [])}

            for tweet in resp.data:
                tid = str(tweet.id)
                if tid in seen:
                    continue
                seen.add(tid)
                author = users_by_id.get(tweet.author_id)
                username = author.username if author else handle

                out.append({
                    "external_id": f"twitter:{tid}",
                    "source": "twitter",
                    "author": username,
                    "text": tweet.text,
                    "url": f"https://x.com/{username}/status/{tid}",
                    "published_at": tweet.created_at if tweet.created_at else None,
                })
        except Exception as e:
            log.warning("twitter_fetch_failed", handle=handle, error=str(e))

    log.info("twitter_fetch_done", count=len(out))
    return out
