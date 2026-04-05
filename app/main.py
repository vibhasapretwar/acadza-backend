"""
Acadza AI Recommender — FastAPI Backend
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import analyze, recommend, question, leaderboard

app = FastAPI(
    title="Acadza AI Recommender",
    description="AI-powered study recommender for JEE/NEET students",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ── CORS — allow Vite dev server + any deployment origin ────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(analyze.router, tags=["Analysis"])
app.include_router(recommend.router, tags=["Recommendations"])
app.include_router(question.router, tags=["Questions"])
app.include_router(leaderboard.router, tags=["Leaderboard"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "ok",
        "service": "Acadza AI Recommender API",
        "version": "1.0.0",
        "endpoints": {
            "analyze":     "POST /analyze/{student_id}",
            "recommend":   "POST /recommend/{student_id}",
            "question":    "GET  /question/{question_id}",
            "leaderboard": "GET  /leaderboard",
            "docs":        "GET  /docs"
        }
    }


@app.get("/students", tags=["Health"])
async def list_students():
    """Helper: list all student IDs and names."""
    from app.services.data_loader import get_students
    students = get_students()
    return [{"student_id": s["student_id"], "name": s["name"]} for s in students]
