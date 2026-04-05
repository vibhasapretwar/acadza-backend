"""
recommender_fixed.py — Debug Task Solution

=============================================================================
BUGS FOUND (3 bugs total — all silent, no errors raised)
=============================================================================

BUG 1 — get_weak_chapters() returns STRONG chapters, not weak ones
─────────────────────────────────────────────────────────────────────────────
Location: get_weak_chapters(), line:
    sorted_chapters = sorted(chapter_avg.items(), key=lambda x: x[1], reverse=True)

What it does:   Sorts chapters in DESCENDING order (highest score first).
                Then returns the first top_n — i.e., the STRONGEST chapters.

What it should: Sort in ASCENDING order (lowest score first) so the weakest
                chapters bubble to the top.

Fix:            reverse=True  →  reverse=False

Why it fooled me / AI:
    The function name is get_weak_chapters and the docstring says "weakest
    chapters (lowest scores first)". The bug is purely in the sort direction —
    the code LOOKS correct at a glance because sorted(..., reverse=True) is
    common and the variable name weak_chapters makes the result seem right.
    The output is plausible numbers and real chapter names, so it silently
    recommends your best chapters instead of your worst ones.

─────────────────────────────────────────────────────────────────────────────

BUG 2 — get_questions_for_chapter() returns _id (OID) instead of qid
─────────────────────────────────────────────────────────────────────────────
Location: get_questions_for_chapter(), line:
    qid = q.get("_id", "")
    if isinstance(qid, dict):
        qid = qid.get("$oid", "")

What it does:   Extracts the MongoDB ObjectID (a random hex string) as the
                question identifier and returns it.

What it should: Return the human-readable qid field (e.g. "Q_PHY_0042")
                which is what the question lookup endpoint expects.

Fix:            Replace with   qid = q.get("qid", "")
                (no need to unwrap _id at all here)

Why it fooled me / AI:
    The variable is named qid and the _id field is indeed an identifier, so
    the intent looks reasonable. The returned list contains valid-looking
    strings (hex hashes), so the output doesn't look wrong. But anyone
    calling GET /question/<id> with that hash will get a 404 — a bug that
    only surfaces at runtime when you try to use the returned IDs.

─────────────────────────────────────────────────────────────────────────────

BUG 3 — get_chapter_scores() gives every chapter in an attempt the FULL
         session score instead of a chapter-proportional score
─────────────────────────────────────────────────────────────────────────────
Location: get_chapter_scores(), inside the loop:
    for chapter in attempt["chapters"]:
        chapter_totals[chapter] += score_pct   # ← full session score

What it does:   If an attempt covers ["Thermodynamics", "Kinematics"] and
                the student scored 40%, BOTH chapters get +40 added to their
                running total. When multiple chapters share an attempt, each
                gets credited the full score — inflating chapters that appear
                together often and making averages unreliable.

What it should: Divide the score equally among all chapters in that attempt
                (a reasonable heuristic when per-chapter breakdown isn't
                available):
                    per_chapter_score = score_pct / len(attempt["chapters"])
                    chapter_totals[chapter] += per_chapter_score

Fix:            Add:  num_chapters = max(len(attempt["chapters"]), 1)
                Then: chapter_totals[chapter] += score_pct / num_chapters

Why it fooled me / AI:
    The average still produces reasonable-looking numbers (they're just
    inflated by a factor of ~2). The chapters that appear most often in
    tests get the highest totals, which might accidentally correlate with
    the chapters the student practices most — so the output is plausible
    and not obviously wrong unless you check the math.

=============================================================================
"""

import json
import re
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def load_data():
    with open(os.path.join(DATA_DIR, "student_performance.json")) as f:
        students = json.load(f)
    with open(os.path.join(DATA_DIR, "question_bank.json")) as f:
        questions = json.load(f)
    with open(os.path.join(DATA_DIR, "dost_config.json")) as f:
        dost_config = json.load(f)
    return students, questions, dost_config


def normalize_marks(marks_raw, total_questions=25):
    marks_str = str(marks_raw).strip()

    m = re.match(r'^([+-]?\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*\(', marks_str)
    if m:
        return float(m.group(1)) / float(m.group(2)) * 100

    m = re.match(r'^([+-]?\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)$', marks_str)
    if m:
        return float(m.group(1)) / float(m.group(2)) * 100

    m = re.match(r'^\+(\d+)\s+-(\d+)$', marks_str)
    if m:
        net = float(m.group(1)) - float(m.group(2))
        return (net / (total_questions * 4)) * 100

    try:
        return (float(marks_str) / (total_questions * 4)) * 100
    except (ValueError, TypeError):
        return 0.0


def get_chapter_scores(student):
    """
    Returns a dict mapping chapter -> average score percentage.
    FIX (Bug 3): Divide session score proportionally among chapters in that attempt.
    """
    chapter_totals = {}
    chapter_counts = {}

    for attempt in student["attempts"]:
        score_pct = normalize_marks(attempt["marks"], attempt["total_questions"])
        num_chapters = max(len(attempt["chapters"]), 1)   # FIX: distribute evenly
        per_chapter_score = score_pct / num_chapters      # FIX: proportional

        for chapter in attempt["chapters"]:
            if chapter not in chapter_totals:
                chapter_totals[chapter] = 0
                chapter_counts[chapter] = 0
            chapter_totals[chapter] += per_chapter_score  # FIX: not full score_pct
            chapter_counts[chapter] += 1

    chapter_avg = {}
    for ch in chapter_totals:
        chapter_avg[ch] = chapter_totals[ch] / chapter_counts[ch]

    return chapter_avg


def get_weak_chapters(chapter_avg, top_n=3):
    """Return the top_n weakest chapters (lowest scores first).
    FIX (Bug 1): reverse=False so lowest scores come first.
    """
    sorted_chapters = sorted(chapter_avg.items(), key=lambda x: x[1], reverse=False)  # FIX
    return [ch for ch, _ in sorted_chapters[:top_n]]


def assign_difficulty(avg_score_pct):
    if avg_score_pct < 35:
        return "easy"
    elif avg_score_pct < 60:
        return "medium"
    else:
        return "hard"


def get_questions_for_chapter(questions, subject, chapter, count=5):
    """Return question IDs (qid field) for a given subject and chapter.
    FIX (Bug 2): use q.get('qid') instead of q.get('_id').
    """
    results = []
    chapter_lower = chapter.lower().replace(" ", "_")

    for q in questions:
        if q.get("subject", "").lower() != subject.lower():
            continue

        qid = q.get("qid", "")   # FIX: use qid, not _id

        topic = q.get("topic", "").lower().replace(" ", "_")
        if chapter_lower in topic:
            if qid:
                results.append(qid)

        if len(results) >= count:
            break

    return results


def recommend(student_id):
    students, questions, dost_config = load_data()

    student = next((s for s in students if s["student_id"] == student_id), None)
    if not student:
        return {"error": f"Student {student_id} not found"}

    chapter_avg = get_chapter_scores(student)
    overall_avg = sum(chapter_avg.values()) / len(chapter_avg) if chapter_avg else 0
    weak_chapters = get_weak_chapters(chapter_avg)  # now correctly returns WEAK chapters

    subject_scores = {}
    for attempt in student["attempts"]:
        subj = attempt["subject"]
        score = normalize_marks(attempt["marks"], attempt["total_questions"])
        if subj not in subject_scores:
            subject_scores[subj] = []
        subject_scores[subj].append(score)

    subject_avg = {s: sum(v)/len(v) for s, v in subject_scores.items()}
    weak_subject = min(subject_avg, key=lambda s: subject_avg[s]) if subject_avg else "Physics"

    steps = []
    difficulty = assign_difficulty(overall_avg)

    for i, chapter in enumerate(weak_chapters[:2]):
        qids = get_questions_for_chapter(questions, weak_subject, chapter, count=10)

        steps.append({
            "step": i + 1,
            "dost_type": "practiceAssignment",
            "target_chapter": chapter,
            "target_subject": weak_subject,
            "difficulty": difficulty,
            "question_ids": qids,
            "reasoning": f"Chapter '{chapter}' has low performance. Practice needed.",
            "message": f"Work on {chapter} to improve your score."
        })

    steps.append({
        "step": len(steps) + 1,
        "dost_type": "practiceTest",
        "target_chapter": "Mixed",
        "target_subject": weak_subject,
        "difficulty": difficulty,
        "question_ids": [],
        "reasoning": "Full test to measure progress.",
        "message": "Take a full mock test to gauge improvement."
    })

    return {
        "student_id": student_id,
        "name": student["name"],
        "overall_avg_score_pct": round(overall_avg, 2),
        "weak_chapters": weak_chapters,
        "steps": steps
    }


if __name__ == "__main__":
    result = recommend("STU_001")
    print(json.dumps(result, indent=2))
