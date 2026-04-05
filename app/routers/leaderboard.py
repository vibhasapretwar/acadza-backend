from fastapi import APIRouter
from app.services.leaderboard import build_leaderboard

router = APIRouter()

@router.get("/leaderboard")
def leaderboard():
    return build_leaderboard()