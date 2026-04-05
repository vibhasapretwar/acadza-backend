from fastapi import APIRouter
from app.services.recommender import recommend_student

router = APIRouter()

@router.post("/recommend/{student_id}")
def recommend(student_id: str):
    return recommend_student(student_id)