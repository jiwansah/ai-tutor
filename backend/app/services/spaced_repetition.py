from datetime import datetime, timedelta, timezone

def next_review(mastery: float, last_review: datetime | None) -> datetime:
    """
    Simple SM-2-inspired scheduling.
    Higher mastery → longer interval.
    """
    if last_review is None:
        interval_days = 1
    else:
        base = max(1, int(mastery * 30))  # 1-30 days
        interval_days = min(60, base)

    return datetime.now(timezone.utc) + timedelta(days=interval_days)