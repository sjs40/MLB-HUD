"""
MLB-HUD FastAPI application entry point.

Run with:
    uvicorn backend.main:app --reload
    # or from within backend/
    uvicorn main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import schedule, pregame, live, adhoc, players, postgame

app = FastAPI(
    title="MLB-HUD",
    description="Baseball analytics API — pitcher vs. batter matchup breakdowns",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(schedule.router)
app.include_router(pregame.router)
app.include_router(live.router)
app.include_router(adhoc.router)
app.include_router(players.router)
app.include_router(postgame.router)


@app.get("/")
def root():
    return {"status": "ok", "app": "MLB-HUD"}
