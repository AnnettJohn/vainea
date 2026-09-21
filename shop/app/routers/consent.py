from fastapi import APIRouter, Form, Request, status
from fastapi.responses import RedirectResponse

from app.core.consent import COOKIE_NAME, ESSENTIAL, GUELTIGE_WERTE, MAX_AGE

router = APIRouter()


def _safe_next(url: str) -> str:
    """Nur lokale Pfade als Rücksprungziel zulassen - sonst ließe sich der
    Banner als offene Weiterleitung auf fremde Seiten missbrauchen."""
    if url and url.startswith("/") and not url.startswith("//"):
        return url
    return "/"


@router.post("/consent")
async def set_consent(request: Request, choice: str = Form(...), next: str = Form("/")):
    """Einwilligungsentscheidung speichern.

    Ein unbekannter Wert fällt bewusst auf "nur essenziell" zurück statt auf
    "alles erlaubt": bei einer manipulierten oder fehlerhaften Eingabe ist
    die datensparsame Variante die richtige.
    """
    wert = choice if choice in GUELTIGE_WERTE else ESSENTIAL

    antwort = RedirectResponse(url=_safe_next(next), status_code=status.HTTP_303_SEE_OTHER)
    antwort.set_cookie(
        COOKIE_NAME,
        wert,
        max_age=MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    return antwort
