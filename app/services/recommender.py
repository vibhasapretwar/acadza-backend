"""
Recommender service — generates a step-by-step DOST plan based on analysis.
"""
import random
from app.services.analyzer import analyze_student
from app.services.data_loader import get_dost_config, get_questions_by_subject_chapter


def _pick_questions(subject: str, chapter: str, count: int = 5, difficulty: int = None) -> list[str]:
    """Pick question IDs from the bank matching subject and roughly the chapter."""
    chapter_lower = chapter.lower().replace(" ", "_").replace("-", "_")
    questions = get_questions_by_subject_chapter(subject=subject)

    matched = []
    for q in questions:
        topic = q.get("topic", "").lower().replace(" ", "_")
        subtopic = q.get("subtopic", "").lower().replace(" ", "_")
        diff = q.get("difficulty")

        # Match topic/subtopic loosely against chapter
        if chapter_lower in topic or chapter_lower in subtopic or \
           any(word in topic for word in chapter_lower.split("_") if len(word) > 3):
            if difficulty is None or diff == difficulty or diff is None:
                matched.append(q.get("qid", ""))

    # Fallback to subject-level if not enough
    if len(matched) < count:
        all_subj = [q.get("qid", "") for q in questions if q.get("qid")]
        random.shuffle(all_subj)
        matched += [q for q in all_subj if q not in matched]

    matched = [q for q in matched if q]
    return matched[:count]


def recommend_student(student_id: str) -> dict:
    analysis = analyze_student(student_id)
    if not analysis or "error" in analysis:
        return {"student_id": student_id, "error": "Could not analyze student"}

    dost_config = get_dost_config()
    steps = []
    step_num = 1

    avg_score = analysis["avg_score_pct"]
    score_trend = analysis["score_trend"]
    speed_status = analysis["speed_status"]
    weaknesses = analysis["weaknesses"]
    strengths = analysis["strengths"]
    completion_rate = analysis["completion_rate_pct"]
    integer_avoidance = analysis["integer_question_avoidance"]
    subject_breakdown = analysis["subject_breakdown"]

    # Determine primary weak subject
    weak_subject = min(subject_breakdown, key=lambda s: subject_breakdown[s]["avg_score_pct"]) \
        if subject_breakdown else "Physics"
    strong_subject = max(subject_breakdown, key=lambda s: subject_breakdown[s]["avg_score_pct"]) \
        if subject_breakdown else "Physics"

    # ── Step 1: Address conceptual gaps in weakest chapter ───────────────────
    if weaknesses:
        weak_ch = weaknesses[0]
        qids = _pick_questions(weak_subject, weak_ch, count=0)
        steps.append({
            "step": step_num,
            "dost_type": "concept",
            "target_subject": weak_subject,
            "target_chapter": weak_ch,
            "params": dost_config["concept"]["params"],
            "question_ids": [],
            "reasoning": f"'{weak_ch}' is your weakest area with consistently low scores. Build conceptual clarity before attempting more questions.",
            "message": f"📚 Let's start by strengthening your foundation in {weak_ch}. Review the core theory first — this will make everything else easier."
        })
        step_num += 1

    # ── Step 2: Formula revision for weak chapter ─────────────────────────────
    if weaknesses:
        weak_ch = weaknesses[0]
        steps.append({
            "step": step_num,
            "dost_type": "formula",
            "target_subject": weak_subject,
            "target_chapter": weak_ch,
            "params": dost_config["formula"]["params"],
            "question_ids": [],
            "reasoning": "After concept review, consolidating key formulas helps retain what was just learned.",
            "message": f"🔢 Quick formula drill for {weak_ch}. Commit these to memory — they're the shortcuts to faster solving."
        })
        step_num += 1

    # ── Step 3: Practice assignment on weak chapter ───────────────────────────
    if weaknesses:
        weak_ch = weaknesses[0]
        difficulty = "easy" if avg_score < 35 else "medium" if avg_score < 60 else "hard"
        qids = _pick_questions(weak_subject, weak_ch, count=10)
        steps.append({
            "step": step_num,
            "dost_type": "practiceAssignment",
            "target_subject": weak_subject,
            "target_chapter": weak_ch,
            "params": {
                "difficulty": difficulty,
                "type_split": {"scq": 15, "mcq": 5, "integer": 5}
            },
            "question_ids": qids,
            "reasoning": f"Untimed practice on '{weak_ch}' at {difficulty} difficulty — build accuracy without time pressure first.",
            "message": f"✍️ Practice session on {weak_ch}. No timer this time — focus on getting every answer right and understanding why."
        })
        step_num += 1

    # ── Step 4: Integer question fix if avoidance detected ────────────────────
    if integer_avoidance:
        focus_ch = weaknesses[0] if weaknesses else (strengths[0] if strengths else "Kinematics")
        qids = _pick_questions(weak_subject, focus_ch, count=10)
        steps.append({
            "step": step_num,
            "dost_type": "practiceAssignment",
            "target_subject": weak_subject,
            "target_chapter": focus_ch,
            "params": {
                "difficulty": "easy",
                "type_split": {"scq": 0, "mcq": 0, "integer": 10}
            },
            "question_ids": qids[:10],
            "reasoning": "Student is consistently skipping integer-type questions, losing guaranteed marks. Targeted integer practice is essential.",
            "message": "🔢 Integer questions are free marks if you know the concept — let's fix that avoidance pattern right now."
        })
        step_num += 1

    # ── Step 5: Speed drill if slow ──────────────────────────────────────────
    if speed_status == "slow" or speed_status == "on_track":
        focus_ch = strengths[0] if strengths else (weaknesses[0] if weaknesses else "Kinematics")
        qids = _pick_questions(strong_subject, focus_ch, count=10)
        steps.append({
            "step": step_num,
            "dost_type": "clickingPower",
            "target_subject": strong_subject,
            "target_chapter": focus_ch,
            "params": {"total_questions": 10},
            "question_ids": qids[:10],
            "reasoning": f"Average time per question is {analysis['avg_time_per_question_seconds']}s — above the JEE target of ~90s. Speed drills on familiar topics build response muscle memory.",
            "message": f"⚡ Speed drill time! 10 rapid-fire questions on {focus_ch}. Go fast — don't overthink. Build your clicking reflex."
        })
        step_num += 1

    # ── Step 6: Revision plan for second weakest chapter ─────────────────────
    if len(weaknesses) >= 2:
        weak_ch2 = weaknesses[1]
        steps.append({
            "step": step_num,
            "dost_type": "revision",
            "target_subject": weak_subject,
            "target_chapter": weak_ch2,
            "params": {
                "alloted_days": 3,
                "strategy": 2,
                "daily_time_minutes": 45
            },
            "question_ids": [],
            "reasoning": f"'{weak_ch2}' also needs structured revision. A 3-day plan prevents cramming and ensures retention.",
            "message": f"📅 3-day revision plan for {weak_ch2}. Spread it out — 45 mins/day. Consistency beats cramming every time."
        })
        step_num += 1

    # ── Step 7: MCQ option elimination on second weak chapter ─────────────────
    if len(weaknesses) >= 2:
        weak_ch2 = weaknesses[1]
        qids = _pick_questions(weak_subject, weak_ch2, count=10)
        steps.append({
            "step": step_num,
            "dost_type": "pickingPower",
            "target_subject": weak_subject,
            "target_chapter": weak_ch2,
            "params": dost_config["pickingPower"]["params"],
            "question_ids": qids,
            "reasoning": "MCQ elimination is a critical JEE skill — even partial knowledge should yield the correct answer through elimination.",
            "message": f"🎯 MCQ elimination drill on {weak_ch2}. Learn to use options as hints. Eliminate wrong answers fast."
        })
        step_num += 1

    # ── Step 8: Full mock test to consolidate ─────────────────────────────────
    difficulty = "easy" if avg_score < 30 else "medium" if avg_score < 55 else "hard"
    # Pick a mix of questions from weak chapters
    all_qids = []
    for ch in (weaknesses + strengths)[:3]:
        all_qids += _pick_questions(weak_subject, ch, count=8)
    all_qids = list(dict.fromkeys(all_qids))[:25]  # deduplicate

    steps.append({
        "step": step_num,
        "dost_type": "practiceTest",
        "target_subject": weak_subject,
        "target_chapter": "Mixed",
        "params": {
            "difficulty": difficulty,
            "duration_minutes": 60,
            "paperPattern": "Mains"
        },
        "question_ids": all_qids,
        "reasoning": "After concept + formula + targeted practice, a full timed test measures actual improvement and exam readiness.",
        "message": f"🏁 Full mock test on {weak_subject}! Treat it like the real exam — 60 minutes, no breaks. Let's see the improvement."
    })
    step_num += 1

    # ── Step 9: Speed race to build competitive edge ──────────────────────────
    if avg_score >= 50 or score_trend == "improving":
        focus_ch = strengths[0] if strengths else "Mixed"
        qids = _pick_questions(strong_subject, focus_ch, count=10)
        steps.append({
            "step": step_num,
            "dost_type": "speedRace",
            "target_subject": strong_subject,
            "target_chapter": focus_ch,
            "params": {
                "rank": 100,
                "opponent_type": "bot"
            },
            "question_ids": qids[:10],
            "reasoning": "Competitive racing against a bot builds exam pressure tolerance and improves both speed and accuracy under stress.",
            "message": f"🏆 Race time! Compete against a bot on {focus_ch}. Win to build confidence — JEE is competitive, practice pressure too."
        })

    return {
        "student_id": student_id,
        "name": analysis["name"],
        "generated_at": _today(),
        "summary": {
            "avg_score_pct": avg_score,
            "score_trend": score_trend,
            "primary_weakness": weaknesses[0] if weaknesses else "None identified",
            "primary_strength": strengths[0] if strengths else "None identified",
            "focus_subject": weak_subject,
        },
        "total_steps": len(steps),
        "steps": steps
    }


def _today() -> str:
    from datetime import date
    return date.today().isoformat()
