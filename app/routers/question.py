from fastapi import APIRouter

router = APIRouter()

@router.get("/question/{id}")
def question(id: str):
    return {"message": "Question endpoint placeholder"}