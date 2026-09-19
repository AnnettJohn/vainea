from fastapi import APIRouter, Depends, Request

from app.core.context import get_base_context
from app.core.templates import templates

router = APIRouter()


@router.get("/story")
async def story(request: Request, base_context: dict = Depends(get_base_context)):
    context = {**base_context, "page_title": "Our Story — VAINEA"}
    return templates.TemplateResponse(request, "story.html", context)
