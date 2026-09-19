from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.state import State


async def get_nav_states(db: AsyncSession) -> list[State]:
    """States für die Hauptnavigation, überall in derselben Reihenfolge."""
    result = await db.execute(select(State).order_by(State.sort_order))
    return list(result.scalars().all())
