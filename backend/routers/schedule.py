"""
GET /schedule — today's and tomorrow's games with probable pitchers.
"""

from datetime import date
from fastapi import APIRouter, Query
from typing import Optional

from ..data.mlb_api import get_schedule, get_schedule_two_days

router = APIRouter(tags=["schedule"])


@router.get("/schedule")
def schedule(query_date: Optional[str] = Query(None, alias="date")):
    """
    Return scheduled games.

    - If `date` is provided (YYYY-MM-DD), return that day's games.
    - If omitted, return today's and tomorrow's games combined.
    """
    if query_date:
        return get_schedule(query_date)
    return get_schedule_two_days()
