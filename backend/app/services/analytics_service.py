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


# ─────────────────────────────────────────────────────────────────────
# Resolve concept_key → human-readable label
# ─────────────────────────────────────────────────────────────────────

async def _resolve_concept_labels(
    db: AsyncSession, keys: list[str]
) -> dict[str, str]:
    """
    Map raw concept keys to friendly display names.

    Supported key shapes:
      - "chapter:<uuid>"  → chapter.title
      - "section:<uuid>"  → section.title
      - "subject:<uuid>"  → subject.name
      - "solving_linear_eq" (real concept key) → concepts.name
      - anything else → returned as-is
    """
    from app.db.models.curriculum import Chapter, Section, Subject
    from app.db.models.concept import Concept

    out: dict[str, str] = {}
    chapter_ids, section_ids, subject_ids, concept_keys = [], [], [], []

    for key in keys:
        if not key:
            continue
        if key.startswith("chapter:"):
            chapter_ids.append(key.split(":", 1)[1])
        elif key.startswith("section:"):
            section_ids.append(key.split(":", 1)[1])
        elif key.startswith("subject:"):
            subject_ids.append(key.split(":", 1)[1])
        else:
            concept_keys.append(key)

    if chapter_ids:
        rows = (await db.execute(
            select(Chapter.id, Chapter.title).where(Chapter.id.in_(chapter_ids))
        )).all()
        for cid, title in rows:
            out[f"chapter:{cid}"] = title

    if section_ids:
        rows = (await db.execute(
            select(Section.id, Section.title).where(Section.id.in_(section_ids))
        )).all()
        for sid, title in rows:
            out[f"section:{sid}"] = title

    if subject_ids:
        rows = (await db.execute(
            select(Subject.id, Subject.name).where(Subject.id.in_(subject_ids))
        )).all()
        for sid, name in rows:
            out[f"subject:{sid}"] = name

    if concept_keys:
        rows = (await db.execute(
            select(Concept.key, Concept.name).where(Concept.key.in_(concept_keys))
        )).all()
        for key, name in rows:
            out[key] = name

    # Fall back to the raw key for anything that couldn't be resolved
    for key in keys:
        out.setdefault(key, key)
    return out


def _sanitize_extra(extra: dict) -> dict:
    return {k: v for k, v in (extra or {}).items() if k.lower() not in PII_FIELD_BLOCKLIST}

LEGACY_MODE_MAP = {
    "teacher":   "teaching",
    "socratic":  "teaching",
    "hint":      "teaching",
    "doubt":     "teaching",
    "revision":  "teaching",
    "practice":  "quiz",
    "homework":  "quiz",
}


def _normalize_mode_counts(rows: list[tuple[str, int]]) -> dict[str, int]:
    """Collapse legacy mode names into the current three: teaching, quiz, exam."""
    out: dict[str, int] = {}
    for mode, count in rows:
        key = LEGACY_MODE_MAP.get(mode, mode)
        out[key] = out.get(key, 0) + count
    return out

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

async def school_summary(
    db: AsyncSession, school_id, days: int = 30, class_id=None
) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)

    def _base(stmt):
        stmt = stmt.where(
            AnalyticsEvent.school_id == school_id,
            AnalyticsEvent.created_at >= since,
        )
        if class_id:
            stmt = stmt.where(AnalyticsEvent.class_id == class_id)
        return stmt

    active = (await db.execute(
        _base(select(func.count(distinct(AnalyticsEvent.student_id)))
              .where(AnalyticsEvent.student_id.isnot(None)))
    )).scalar() or 0

    questions = (await db.execute(
        _base(select(func.count()).select_from(AnalyticsEvent)
              .where(AnalyticsEvent.event_type == "question_asked"))
    )).scalar() or 0

    correct = (await db.execute(
        _base(select(func.count()).select_from(AnalyticsEvent)
              .where(AnalyticsEvent.event_type == "answer_evaluated",
                     AnalyticsEvent.is_correct.is_(True)))
    )).scalar() or 0

    verified = (await db.execute(
        _base(select(func.count()).select_from(AnalyticsEvent)
              .where(AnalyticsEvent.was_verified.is_(True)))
    )).scalar() or 0

    mode_rows = (await db.execute(
        _base(select(AnalyticsEvent.mode, func.count())
              .where(AnalyticsEvent.mode.isnot(None))
              .group_by(AnalyticsEvent.mode))
    )).all()

    return {
        "period_days": days,
        "active_students": active,
        "questions_asked": questions,
        "answers_correct": correct,
        "answers_verified": verified,
        "correct_rate": round(correct / questions, 3) if questions else 0.0,
        "verified_rate": round(verified / questions, 3) if questions else 0.0,
        "mode_distribution": _normalize_mode_counts(mode_rows),
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

    # Resolve keys → labels (one batch query)
    all_keys = [c for c, _ in top_rows]
    label_map = await _resolve_concept_labels(db, all_keys)

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

    # k-anonymity threshold. Classrooms often have fewer than 5 attempts per
    # concept in a 30-day window, so 3 is a safer floor for a demo/school.
    MIN_ATTEMPTS = 3

    weak = []
    for concept, total, correct in weak_rows:
        if not total:
            continue
        rate = (correct or 0) / total
        if total >= MIN_ATTEMPTS:
            weak.append({
                "concept": concept,  # raw key, resolved later
                "concept_key": concept,
                "attempts": total,
                "correct_rate": round(rate, 3),
            })
    weak.sort(key=lambda x: x["correct_rate"])
    weak = weak[:10]

    return {
        "period_days": days,
        "active_students": active,
        "questions_asked": questions,
        "top_concepts": [
            {
                "concept": label_map.get(c, c),
                "concept_key": c,
                "count": n,
            }
            for c, n in top_rows
        ],
        "weak_concepts": [
            {
                **w,
                "concept": label_map.get(w["concept_key"], w["concept_key"]),
            }
            for w in weak
        ],
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
