import re

def normalize_marks(marks_raw, total_questions=25):
    marks_str = str(marks_raw).strip()

    m = re.match(r'^([+-]?\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*\(', marks_str)
    if m:
        raw = float(m.group(1))
        max_score = float(m.group(2))
        pct = (raw / max_score) * 100 if max_score else 0
        return {
            "percentage": round(pct, 2),
            "raw_score": raw,
            "max_score": max_score
        }

    m = re.match(r'^([+-]?\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)$', marks_str)
    if m:
        raw = float(m.group(1))
        max_score = float(m.group(2))
        pct = (raw / max_score) * 100 if max_score else 0
        return {
            "percentage": round(pct, 2),
            "raw_score": raw,
            "max_score": max_score
        }

    m = re.match(r'^\+(\d+)\s+-(\d+)$', marks_str)
    if m:
        raw = float(m.group(1)) - float(m.group(2))
        max_score = total_questions * 4
        pct = (raw / max_score) * 100 if max_score else 0
        return {
            "percentage": round(pct, 2),
            "raw_score": raw,
            "max_score": max_score
        }

    try:
        raw = float(marks_str)
        max_score = total_questions * 4
        pct = (raw / max_score) * 100 if max_score else 0
        return {
            "percentage": round(pct, 2),
            "raw_score": raw,
            "max_score": max_score
        }
    except (ValueError, TypeError):
        return {
            "percentage": 0.0,
            "raw_score": 0.0,
            "max_score": 0.0
        }