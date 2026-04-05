"""
Leaderboard service — ranks all students with a composite scoring formula.

Scoring formula (100 pts max):
  - Average score %        → 40 pts  (weighted most heavily — raw performance)
  - Completion rate %      → 20 pts  (finishing tests shows discipline)
  - Attempt rate %         → 15 pts  (not skipping questions)
  - Recency bonus          → 15 pts  (recent improvement trend)
  - Speed score            → 10 pts  (avg_time efficiency, capped)
"""
from app.services.analyzer import analyze_student
from app.services.data_loader import get_students


def _speed_score(avg_time_sec: float) -> float:
    """Convert avg time per question to a 0-10 score. Target = 90s."""
    if avg_time_sec <= 0:
        return 5.0
    if avg_time_sec <= 60:
        return 10.0
    elif avg_time_sec <= 90:
        return 8.0
    elif avg_time_sec <= 120:
        return 6.0
    elif avg_time_sec <= 150:
        return 4.0
    elif avg_time_sec <= 200:
        return 2.0
    return 1.0


def _trend_score(trend: str, recent_avg: float, overall_avg: float) -> float:
    """0-15 pts for trend and recent performance."""
    if trend == "improving":
        base = 15.0
    elif trend == "stable":
        base = 8.0
    else:
        base = 3.0

    # Bonus if recent avg is above overall avg
    if recent_avg > overall_avg + 5:
        base = min(15.0, base + 3)
    return base


def build_leaderboard() -> dict:
    students = get_students()
    entries = []

    for student in students:
        sid = student["student_id"]
        analysis = analyze_student(sid)
        if not analysis or "error" in analysis:
            continue

        avg_score = analysis["avg_score_pct"]
        recent_avg = analysis["recent_avg_score_pct"]
        completion = analysis["completion_rate_pct"]
        attempt_rate = analysis["avg_attempt_rate_pct"]
        speed = _speed_score(analysis["avg_time_per_question_seconds"])
        trend = analysis["score_trend"]

        # Score components
        score_component = round(avg_score * 0.40, 2)          # max 40
        completion_component = round(completion * 0.20, 2)    # max 20
        attempt_component = round(attempt_rate * 0.15, 2)     # max 15
        trend_component = round(_trend_score(trend, recent_avg, avg_score), 2)  # max 15
        speed_component = round(speed, 2)                     # max 10

        total_score = round(
            score_component + completion_component + attempt_component +
            trend_component + speed_component, 2
        )

        entries.append({
            "student_id": sid,
            "name": analysis["name"],
            "total_score": total_score,
            "score_breakdown": {
                "avg_score_pts": score_component,
                "completion_pts": completion_component,
                "attempt_rate_pts": attempt_component,
                "trend_pts": trend_component,
                "speed_pts": speed_component
            },
            "stats": {
                "avg_score_pct": avg_score,
                "recent_avg_pct": recent_avg,
                "completion_rate_pct": completion,
                "attempt_rate_pct": attempt_rate,
                "speed_status": analysis["speed_status"],
                "score_trend": trend,
                "total_attempts": analysis["total_attempts"]
            },
            "strength": analysis["strengths"][0] if analysis["strengths"] else "—",
            "weakness": analysis["weaknesses"][0] if analysis["weaknesses"] else "—",
            "focus_area": analysis["weaknesses"][0] if analysis["weaknesses"] else
                          (analysis["strengths"][-1] if analysis["strengths"] else "General Practice")
        })

    # Sort by total_score descending, name ascending for ties
    entries.sort(key=lambda x: (-x["total_score"], x["name"]))

    for i, entry in enumerate(entries):
        entry["rank"] = i + 1

    return {
        "leaderboard": entries,
        "total_students": len(entries),
        "scoring_formula": {
            "avg_score": "40 pts (performance weight)",
            "completion_rate": "20 pts (discipline)",
            "attempt_rate": "15 pts (engagement)",
            "trend": "15 pts (improvement)",
            "speed": "10 pts (efficiency)"
        }
    }
