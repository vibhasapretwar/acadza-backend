import json
import os
from functools import lru_cache

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")


def _load_json(file_name: str):
    path = os.path.join(DATA_DIR, file_name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def get_students():
    return _load_json("student_performance.json")


@lru_cache
def get_student_by_id():
    students = get_students()
    return {s["student_id"]: s for s in students}


@lru_cache
def get_dost_config():
    return _load_json("dost_config.json")


@lru_cache
def get_question_bank():
    return _load_json("question_bank.json")


def get_questions_by_subject_chapter(subject=None):
    questions = get_question_bank()
    if subject:
        return [q for q in questions if q.get("subject", "").lower() == subject.lower()]
    return questions