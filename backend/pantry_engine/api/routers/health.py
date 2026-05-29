from fastapi import APIRouter

from pantry_engine.db import check_connection

router = APIRouter(tags=["health"])


@router.get("/api/health/db")
def health_db():
    return check_connection()
