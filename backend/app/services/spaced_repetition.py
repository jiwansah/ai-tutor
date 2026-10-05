from datetime import datetime, timedelta, timezone


def next_review(mastery: float, last_review=None) -> datetime:
    base = max(1, int(mastery * 30))
    return datetime.now(timezone.utc) + timedelta(days=min(60, base))
