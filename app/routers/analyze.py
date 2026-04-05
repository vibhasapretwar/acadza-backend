from fastapi import APIRouter
from app.services.analyzer import analyze_student

router = APIRouter()

@router.post("/analyze/{student_id}")
def analyze(student_id: str):
    result = analyze_student(student_id)
    if not result:
        return {"error": f"Student {student_id} not found"}
    return result