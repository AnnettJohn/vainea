from fastapi import APIRouter, Depends, Request

from app.core.context import get_base_context
from app.core.templates import templates

router = APIRouter()

# Markenclaims 1:1 aus storyPageHtml() des Click-Dummys - redaktioneller
# Text ohne eigene Entität im Datenmodell.
PILLARS = [
    (
        "01",
        "Langsamkeit als Haltung",
        "Wir glauben, dass die schönsten Momente die sind, für die man sich Zeit nimmt. "
        "Kein Trend, keine Eile — nur der bewusste Wechsel vom Tun ins Sein.",
    ),
    (
        "02",
        "Material mit Bedeutung",
        "Jedes Piece ist so gemacht, dass es sich auf der Haut richtig anfühlt: weiche "
        "Frottee-Qualitäten, klare Silhouetten, Farben, die eine Stimmung tragen statt nur zu dekorieren.",
    ),
    (
        "03",
        "Design, das sich gut anfühlt",
        "Form folgt Gefühl. Wir gestalten nicht für den Laufsteg, sondern für den Moment "
        "danach — barfuß, warm, angekommen.",
    ),
]


@router.get("/story")
async def story(request: Request, base_context: dict = Depends(get_base_context)):
    context = {
        **base_context,
        "pillars": PILLARS,
        "page_title": "Our Story — VAINEA",
        "page_description": (
            "Warum es VAINEA gibt: vier States, drei Haltungen und der Wunsch, "
            "den Moment nach dem Wasser anziehbar zu machen."
        ),
    }
    return templates.TemplateResponse(request, "story.html", context)
