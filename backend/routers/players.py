"""
GET /players/search — player name search for ad hoc mode.
"""

from fastapi import APIRouter, Query
from ..data.mlb_api import search_players

router = APIRouter(tags=["players"])


@router.get("/players/search")
def player_search(q: str = Query(..., min_length=2, description="Player name to search")):
    """Search for MLB players by name. Returns id, name, position, handedness."""
    return search_players(q)
