from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import get_base_context
from app.core.legal import render_legal_body
from app.core.templates import templates
from app.db.session import get_db
from app.models.legal import LegalPage

router = APIRouter(prefix="/legal")


@router.get("/{slug}")
async def legal_page(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    base_context: dict = Depends(get_base_context),
):
    """Rechtsseite aus der Datenbank ausliefern.

    Unveröffentlichte Seiten geben 200 mit einem Hinweis zurück, nicht 404:
    der Link im Footer soll nicht ins Leere laufen, und die Seite existiert
    ja - ihr Text ist nur noch in juristischer Prüfung.
    """
    result = await db.execute(select(LegalPage).where(LegalPage.slug == slug))
    seite = result.scalar_one_or_none()
    if seite is None:
        raise HTTPException(status_code=404, detail="Seite nicht gefunden")

    context = {
        **base_context,
        "seite": seite,
        "body_html": render_legal_body(seite.body) if seite.is_published else "",
        "page_title": f"{seite.meta_title or seite.title} — VAINEA",
        "page_description": seite.meta_description,
        "canonical_url": str(request.url_for("legal_page", slug=seite.slug)),
    }
    return templates.TemplateResponse(request, "legal_page.html", context)
