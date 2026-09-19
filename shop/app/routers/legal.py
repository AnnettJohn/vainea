from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.context import get_base_context
from app.core.templates import templates

router = APIRouter(prefix="/legal")

# Platzhalter, bis geprüfte Rechtstexte vorliegen (siehe Pflichtenheft,
# offener Punkt). Struktur/Routing steht bereits, Inhalte folgen später ohne
# Codeänderung.
PAGES = {
    "impressum": "Impressum",
    "datenschutz": "Datenschutzerklärung",
    "agb": "AGB",
    "widerruf": "Widerrufsbelehrung",
}


@router.get("/{page}")
async def legal_page(page: str, request: Request, base_context: dict = Depends(get_base_context)):
    title = PAGES.get(page)
    if title is None:
        raise HTTPException(status_code=404, detail="Seite nicht gefunden")

    context = {**base_context, "legal_title": title, "page_title": f"{title} — VAINEA"}
    return templates.TemplateResponse(request, "legal_page.html", context)
