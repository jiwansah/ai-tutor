"""
Privacy-safe analytics.
- Logs only IDs, enums, and safe measures — never PII or chat text.
- All dashboards use aggregations; no individual student data.
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, distinct, desc, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.analytics import AnalyticsEvent, DailyRollup


# ------------------------------------------------------------------
# Event logging (fire-and-forget — caller commits)
# ------------------------------------------------------------------

PII_FIELD_BLOCKLIST = {"email", "full_name", "password", "phone", "address", "chat", "text"}


def _sanitize_extra(extra: dict) -> dict:
    return {k: v for k, v in (extra or {}).items() if k.lower() not in PII_FIELD_BLOCKLIST}


async def log_event(
    db: AsyncSession,
    *,
    event_type: str,
    student_id=None,
    school_id=None,
    class_id=None,
    subject_id=None,
    chapter_id=None,
    section_id=None,
    concept_key=None,
    mode=None,
    is_correct=None,
    was_verified=None,
    duration_ms=None,
    token_count=None,
    extra: dict | None = None,
) -> None:
    db.add(AnalyticsEvent(
        event_type=event_type,
        student_id=student_id,
        school_id=school_id,
        class_id=class_id,
        subject_id=subject_id,
        chapter_id=chapter_id,
        section_id=section_id,
        concept_key=concept_key,
        mode=mode,
        is_correct=is_correct,
        was_verified=was_verified,
        duration_ms=duration_ms,
        token_count=token_count,
        extra=_sanitize_extra(extra or {}),
    ))


# ------------------------------------------------------------------
# School-level summary
# ------------------------------------------------------------------

async def school_summary(db: AsyncSession, school_id, days: int = 30) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)

    active = (await db.execute(
        select(func.count(distinct(AnalyticsEvent.student_id)))
        .where(AnalyticsEvent.school_id == school_id,
               AnalyticsEvent.created_at >= since,
               AnalyticsEvent.student_id.isnot(None))
    )).scalar() or 0

    questions = (await db.execute(
        select(func.count()).select_from(AnalyticsEvent)
        .where(AnalyticsEvent.school_id == school_id,
               AnalyticsEvent.created_at >= since,
               AnalyticsEvent.event_type == "question_asked")
    )).scalar() or 0

    correct = (await db.execute(
        select(func.count()).select_from(AnalyticsEvent)
        .where(AnalyticsEvent.school_id == school_id,
               AnalyticsEvent.created_at >= since,
               AnalyticsEvent.event_type == "answer_evaluated",
               AnalyticsEvent.is_correct.is_(True))
    )).scalar() or 0

    verified = (await db.execute(
        select(func.count()).select_from(AnalyticsEvent)
        .where(AnalyticsEvent.school_id == school_id,
               AnalyticsEvent.created_at >= since,
               AnalyticsEvent.was_verified.is_(True))
    )).scalar() or 0

    mode_rows = (await db.execute(
        select(AnalyticsEvent.mode, func.count())
        .where(AnalyticsEvent.school_id == school_id,
               AnalyticsEvent.created_at >= since,
               AnalyticsEvent.mode.isnot(None))
        .group_by(AnalyticsEvent.mode)
    )).all()

    return {
        "period_days": days,
        "active_students": active,
        "questions_asked": questions,
        "answers_correct": correct,
        "answers_verified": verified,
        "correct_rate": round(correct / questions, 3) if questions else 0.0,
        "verified_rate": round(verified / questions, 3) if questions else 0.0,
        "mode_distribution": {m: c for m, c in mode_rows},
    }


# ------------------------------------------------------------------
# Class-level summary
# ------------------------------------------------------------------

async def class_summary(db: AsyncSession, class_id, days: int = 30) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)

    active = (await db.execute(
        select(func.count(distinct(AnalyticsEvent.student_id)))
        .where(AnalyticsEvent.class_id == class_id,
               AnalyticsEvent.created_at >= since,
               AnalyticsEvent.student_id.isnot(None))
    )).scalar() or 0

    questions = (await db.execute(
        select(func.count()).select_from(AnalyticsEvent)
        .where(AnalyticsEvent.class_id == class_id,
               AnalyticsEvent.created_at >= since,
               AnalyticsEvent.event_type == "question_asked")
    )).scalar() or 0

    # Top concepts asked about
    top_rows = (await db.execute(
        select(AnalyticsEvent.concept_key, func.count().label("cnt"))
        .where(AnalyticsEvent.class_id == class_id,
               AnalyticsEvent.created_at >= since,
               AnalyticsEvent.concept_key.isnot(None))
        .group_by(AnalyticsEvent.concept_key)
        .order_by(desc("cnt"))
        .limit(10)
    )).all()

    # Weak concepts — correct_rate per concept, using CASE for boolean->int
    correct_as_int = case((AnalyticsEvent.is_correct.is_(True), 1), else_=0)

    weak_rows = (await db.execute(
        select(
            AnalyticsEvent.concept_key,
            func.count().label("total"),
            func.sum(correct_as_int).label("correct"),
        )
        .where(AnalyticsEvent.class_id == class_id,
               AnalyticsEvent.created_at >= since,
               AnalyticsEvent.concept_key.isnot(None),
               AnalyticsEvent.is_correct.isnot(None))
        .group_by(AnalyticsEvent.concept_key)
    )).all()

    weak = []
    for concept, total, correct in weak_rows:
        if not total:
            continue
        rate = (correct or 0) / total
        # k-anonymity: only include if enough attempts
        if total >= 5:
            weak.append({
                "concept": concept,
                "attempts": total,
                "correct_rate": round(rate, 3),
            })
    weak.sort(key=lambda x: x["correct_rate"])
    weak = weak[:10]

    return {
        "period_days": days,
        "active_students": active,
        "questions_asked": questions,
        "top_concepts": [{"concept": c, "count": n} for c, n in top_rows],
        "weak_concepts": weak,
    }


# ------------------------------------------------------------------
# Daily rollup (run nightly via cron / Celery / manual trigger)
# ------------------------------------------------------------------

async def compute_daily_rollup(db: AsyncSession, day: str) -> None:
    """
    Pre-aggregate one day's events into analytics_daily_rollups.
    day format: "YYYY-MM-DD"
    """
    start = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    schools = (await db.execute(
        select(distinct(AnalyticsEvent.school_id))
        .where(AnalyticsEvent.created_at >= start,
               AnalyticsEvent.created_at < end)
    )).scalars().all()

    for school_id in schools:
        if school_id is None:
            continue

        events = list((await db.execute(
            select(AnalyticsEvent)
            .where(AnalyticsEvent.school_id == school_id,
                   AnalyticsEvent.created_at >= start,
                   AnalyticsEvent.created_at < end)
        )).scalars().all())

        active = len({e.student_id for e in events if e.student_id})
        questions = sum(1 for e in events if e.event_type == "question_asked")
        correct = sum(1 for e in events if e.event_type == "answer_evaluated" and e.is_correct)
        verified = sum(1 for e in events if e.was_verified)

        durations = [e.duration_ms for e in events if e.duration_ms]
        avg_ms = sum(durations) / len(durations) if durations else 0.0

        mode_counts: dict = {}
        concept_counts: dict = {}
        for e in events:
            if e.mode:
                mode_counts[e.mode] = mode_counts.get(e.mode, 0) + 1
            if e.concept_key:
                concept_counts[e.concept_key] = concept_counts.get(e.concept_key, 0) + 1

        top_concepts = sorted(concept_counts.items(), key=lambda x: -x[1])[:10]

        existing = (await db.execute(
            select(DailyRollup).where(
                DailyRollup.day == day,
                DailyRollup.school_id == school_id,
            )
        )).scalar_one_or_none()

        sessions_started = sum(1 for e in events if e.event_type == "session_started")

        if existing:
            existing.active_students = active
            existing.sessions_started = sessions_started
            existing.questions_asked = questions
            existing.answers_correct = correct
            existing.answers_verified = verified
            existing.avg_response_ms = avg_ms
            existing.mode_counts = mode_counts
            existing.top_concepts = [{"concept": c, "count": n} for c, n in top_concepts]
        else:
            db.add(DailyRollup(
                day=day,
                school_id=school_id,
                active_students=active,
                sessions_started=sessions_started,
                questions_asked=questions,
                answers_correct=correct,
                answers_verified=verified,
                avg_response_ms=avg_ms,
                mode_counts=mode_counts,
                top_concepts=[{"concept": c, "count": n} for c, n in top_concepts],
            ))

    await db.commit()


# ------------------------------------------------------------------
# Trend (last N days of rollups)
# ------------------------------------------------------------------

async def school_trend(db: AsyncSession, school_id, days: int = 14) -> list[dict]:
    rows = (await db.execute(
        select(DailyRollup)
        .where(DailyRollup.school_id == school_id)
        .order_by(DailyRollup.day.desc())
        .limit(days)
    )).scalars().all()

    return [
        {
            "day": r.day,
            "active_students": r.active_students,
            "questions_asked": r.questions_asked,
            "correct_rate": round(r.answers_correct / r.questions_asked, 3)
                            if r.questions_asked else 0.0,
        }
        for r in reversed(rows)
    ]
