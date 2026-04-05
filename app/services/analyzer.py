"""
Analyzer service — processes student performance data and returns patterns/insights.
"""
from collections import defaultdict
from app.services.data_loader import get_student_by_id
from app.utils.marks_normalizer import normalize_marks


def analyze_student(student_id: str) -> dict:
    students = get_student_by_id()
    student = students.get(student_id)
    if not student:
        return None

    attempts = student.get("attempts", [])
    if not attempts:
        return {"student_id": student_id, "error": "No attempts found"}

    # ── Per-attempt normalized data ──────────────────────────────────────────
    normalized_attempts = []
    for att in attempts:
        nm = normalize_marks(att.get("marks", 0), att.get("total_questions", 25))
        normalized_attempts.append({**att, "normalized_marks": nm})

    # ── Overall score trend ──────────────────────────────────────────────────
    percentages = [a["normalized_marks"]["percentage"] for a in normalized_attempts]
    score_trend = "improving" if len(percentages) > 1 and percentages[-1] > percentages[0] else \
                  "declining" if len(percentages) > 1 and percentages[-1] < percentages[0] else "stable"

    avg_score = round(sum(percentages) / len(percentages), 2) if percentages else 0

    # ── Chapter-wise breakdown ───────────────────────────────────────────────
    chapter_stats = defaultdict(lambda: {"attempts": 0, "total_pct": 0.0, "completed": 0, "aborted": 0})
    subject_stats = defaultdict(lambda: {"attempts": 0, "total_pct": 0.0})

    for att in normalized_attempts:
        pct = att["normalized_marks"]["percentage"]
        subj = att.get("subject", "Unknown")
        subject_stats[subj]["attempts"] += 1
        subject_stats[subj]["total_pct"] += pct

        for ch in att.get("chapters", []):
            chapter_stats[ch]["attempts"] += 1
            chapter_stats[ch]["total_pct"] += pct
            if att.get("completed"):
                chapter_stats[ch]["completed"] += 1
            else:
                chapter_stats[ch]["aborted"] += 1

    chapter_breakdown = {}
    for ch, s in chapter_stats.items():
        avg = round(s["total_pct"] / s["attempts"], 2) if s["attempts"] else 0
        chapter_breakdown[ch] = {
            "attempts": s["attempts"],
            "avg_score_pct": avg,
            "completed": s["completed"],
            "aborted": s["aborted"],
            "status": "strong" if avg >= 60 else "needs_work" if avg >= 35 else "weak"
        }

    subject_breakdown = {}
    for subj, s in subject_stats.items():
        avg = round(s["total_pct"] / s["attempts"], 2) if s["attempts"] else 0
        subject_breakdown[subj] = {"attempts": s["attempts"], "avg_score_pct": avg}

    # ── Strengths and weaknesses ─────────────────────────────────────────────
    sorted_chapters = sorted(chapter_breakdown.items(), key=lambda x: x[1]["avg_score_pct"], reverse=True)
    strengths = [ch for ch, d in sorted_chapters if d["avg_score_pct"] >= 55][:3]
    weaknesses = [ch for ch, d in sorted_chapters if d["avg_score_pct"] < 40][:3]

    # ── Completion rate ──────────────────────────────────────────────────────
    completed = sum(1 for a in attempts if a.get("completed"))
    completion_rate = round((completed / len(attempts)) * 100, 1) if attempts else 0

    # ── Attempt rate (attempted/total) ───────────────────────────────────────
    avg_attempt_rate = round(
        sum(a["attempted"] / a["total_questions"] * 100 for a in attempts if a["total_questions"] > 0)
        / len(attempts), 1
    ) if attempts else 0

    # ── Speed analysis ───────────────────────────────────────────────────────
    avg_time = round(
        sum(a.get("avg_time_per_question_seconds", 0) for a in attempts) / len(attempts), 1
    ) if attempts else 0
    speed_status = "fast" if avg_time < 90 else "on_track" if avg_time < 150 else "slow"

    # ── Integer question avoidance ───────────────────────────────────────────
    integer_avoidance = False
    for att in attempts:
        split = att.get("question_type_split", {})
        attempted_split = att.get("attempted_type_split", {})
        if split.get("integer", 0) > 0:
            attempted_int = attempted_split.get("integer", 0)
            total_int = split.get("integer", 0)
            if total_int > 0 and (attempted_int / total_int) < 0.5:
                integer_avoidance = True
                break

    # ── Recent trend (last 3 attempts) ───────────────────────────────────────
    recent = normalized_attempts[-3:]
    recent_avg = round(sum(a["normalized_marks"]["percentage"] for a in recent) / len(recent), 2) if recent else 0

    # ── Patterns ─────────────────────────────────────────────────────────────
    patterns = []
    if score_trend == "declining":
        patterns.append("Score declining over recent sessions — possible burnout or concept gaps.")
    if completion_rate < 70:
        patterns.append("Frequent test abortions — may indicate confidence issues or time management problems.")
    if avg_attempt_rate < 75:
        patterns.append("Low attempt rate — skipping many questions, likely avoiding harder types.")
    if integer_avoidance:
        patterns.append("Consistently skipping integer-type questions — needs targeted integer practice.")
    if speed_status == "slow":
        patterns.append("Average time per question is high — speed improvement required.")
    if speed_status == "fast" and avg_score < 40:
        patterns.append("Answering quickly but scoring low — possible random guessing pattern.")
    if not patterns:
        patterns.append("Consistent performance across sessions.")

    return {
        "student_id": student_id,
        "name": student["name"],
        "stream": student.get("stream", "JEE"),
        "total_attempts": len(attempts),
        "avg_score_pct": avg_score,
        "recent_avg_score_pct": recent_avg,
        "score_trend": score_trend,
        "completion_rate_pct": completion_rate,
        "avg_attempt_rate_pct": avg_attempt_rate,
        "avg_time_per_question_seconds": avg_time,
        "speed_status": speed_status,
        "integer_question_avoidance": integer_avoidance,
        "subject_breakdown": subject_breakdown,
        "chapter_breakdown": chapter_breakdown,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "patterns": patterns,
        "attempts_detail": [
            {
                "attempt_id": a["attempt_id"],
                "date": a["date"],
                "subject": a["subject"],
                "chapters": a["chapters"],
                "score_pct": a["normalized_marks"]["percentage"],
                "raw_score": a["normalized_marks"]["raw_score"],
                "max_score": a["normalized_marks"]["max_score"],
                "completed": a["completed"],
                "attempted": a["attempted"],
                "total": a["total_questions"],
                "avg_time_sec": a.get("avg_time_per_question_seconds", 0),
            }
            for a in normalized_attempts
        ]
    }
