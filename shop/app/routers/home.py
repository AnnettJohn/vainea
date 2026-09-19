from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import get_base_context
from app.core.templates import templates
from app.db.session import get_db
from app.models.state import State

router = APIRouter()


@router.get("/")
async def home(request: Request, db: AsyncSession = Depends(get_db), base_context: dict = Depends(get_base_context)):
    result = await db.execute(select(State).order_by(State.sort_order))
    states = result.scalars().all()
    context = {
        **base_context,
        "states": states,
        "nav_states": states,  # bereits geladen, keine zweite Abfrage nötig
        "page_title": "VAINEA — Wear Your State of Mind",
    }
    return templates.TemplateResponse(request, "home.html", context)
