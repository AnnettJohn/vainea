from types import SimpleNamespace
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from fastapi_users import exceptions as fastapi_users_exceptions
from fastapi_users.manager import BaseUserManager
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.context import get_base_context
from app.core.templates import templates
from app.core.users import cookie_backend, current_user_optional, get_jwt_strategy, get_user_manager
from app.db.session import get_db
from app.models.order import Order
from app.models.user import User
from app.models.wishlist import WishlistItem
from app.schemas.user import UserCreate

router = APIRouter(prefix="/account")


def _safe_next(url: str) -> str:
    """Nur lokale Pfade als Redirect-Ziel zulassen (kein Open Redirect über
    ?next=https://andere-domain oder einen Referer-Header einer fremden Seite)."""
    if url and url.startswith("/") and not url.startswith("//"):
        return url
    return "/account"


def _safe_referer_path(referer: str) -> str:
    """Referer-Header (volle URL) auf einen lokalen Pfad reduzieren, z. B. um
    nach einer Wishlist-Aktion zur PDP zurückzuspringen."""
    if not referer:
        return "/account"
    path = urlparse(referer).path
    return _safe_next(path)


def _login_redirect(request: Request) -> RedirectResponse:
    """Statt eines rohen 401-Fehlers auf serverseitig gerenderten Seiten: zum
    Login schicken und danach zur ursprünglich gewünschten Seite zurück."""
    return RedirectResponse(
        url=f"/account/login?next={_safe_next(request.url.path)}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/login")
async def login_form(request: Request, next: str = "/account", base_context: dict = Depends(get_base_context)):
    next_url = _safe_next(next)
    if base_context["current_user"] is not None:
        return RedirectResponse(url=next_url, status_code=status.HTTP_303_SEE_OTHER)
    context = {**base_context, "error": None, "next": next_url, "page_title": "Login — VAINEA"}
    return templates.TemplateResponse(request, "account_login.html", context)


@router.post("/login")
async def login_submit(
    request: Request,
    base_context: dict = Depends(get_base_context),
    user_manager: BaseUserManager = Depends(get_user_manager),
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/account"),
):
    next_url = _safe_next(next)
    user = await user_manager.authenticate(SimpleNamespace(username=email, password=password))
    if user is None or not user.is_active:
        context = {
            **base_context,
            "error": "E-Mail oder Passwort ist falsch.",
            "next": next_url,
            "page_title": "Login — VAINEA",
        }
        return templates.TemplateResponse(request, "account_login.html", context, status_code=400)

    strategy = get_jwt_strategy()
    response = await cookie_backend.login(strategy, user)
    response.status_code = status.HTTP_303_SEE_OTHER
    response.headers["location"] = next_url
    return response


@router.get("/register")
async def register_form(request: Request, base_context: dict = Depends(get_base_context)):
    if base_context["current_user"] is not None:
        return RedirectResponse(url="/account", status_code=status.HTTP_303_SEE_OTHER)
    context = {**base_context, "error": None, "page_title": "Konto erstellen — VAINEA"}
    return templates.TemplateResponse(request, "account_register.html", context)


@router.post("/register")
async def register_submit(
    request: Request,
    base_context: dict = Depends(get_base_context),
    user_manager: BaseUserManager = Depends(get_user_manager),
    email: str = Form(...),
    password: str = Form(...),
):
    async def render_error(message: str):
        context = {**base_context, "error": message, "page_title": "Konto erstellen — VAINEA"}
        return templates.TemplateResponse(request, "account_register.html", context, status_code=400)

    try:
        user = await user_manager.create(UserCreate(email=email, password=password))
    except fastapi_users_exceptions.UserAlreadyExists:
        return await render_error("Für diese E-Mail existiert bereits ein Konto.")
    except fastapi_users_exceptions.InvalidPasswordException as exc:
        reason = exc.reason
        return await render_error(" ".join(str(r) for r in reason) if isinstance(reason, list) else str(reason))

    strategy = get_jwt_strategy()
    response = await cookie_backend.login(strategy, user)
    response.status_code = status.HTTP_303_SEE_OTHER
    response.headers["location"] = "/account"
    return response


@router.post("/logout")
async def logout():
    response = await cookie_backend.transport.get_logout_response()
    response.status_code = status.HTTP_303_SEE_OTHER
    response.headers["location"] = "/"
    return response


async def _account_context(request: Request, db: AsyncSession, user: User, **extra) -> dict:
    """Kontext der Kontoseite. Wird sowohl beim normalen Aufruf als auch beim
    erneuten Anzeigen nach einem Fehler gebraucht."""
    orders_result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
    )
    orders = orders_result.scalars().all()

    wishlist_result = await db.execute(
        select(WishlistItem)
        .options(selectinload(WishlistItem.product))
        .where(WishlistItem.user_id == user.id)
        .order_by(WishlistItem.created_at.desc())
    )

    # Kein eigenes Adressbuch-Modell (siehe Pflichtenheft-Datenmodell) - die
    # zuletzt verwendeten Liefer-/Rechnungsadressen stammen aus den fixierten
    # Bestelldaten.
    addresses = [
        {
            "name": o.shipping_name,
            "street": o.shipping_street,
            "zip": o.shipping_zip,
            "city": o.shipping_city,
            "country": o.shipping_country,
        }
        for o in orders[:5]
    ]

    return {
        **await get_base_context(request, db, user),
        "orders": orders,
        "wishlist": wishlist_result.scalars().all(),
        "addresses": addresses,
        "page_title": "Mein Konto — VAINEA",
        **extra,
    }


@router.post("/delete")
async def delete_account(
    request: Request,
    db: AsyncSession = Depends(get_db),
    bestaetigung: str = Form("", alias="confirm"),
    user: User | None = Depends(current_user_optional),
):
    """Kundenkonto löschen (Art. 17 DSGVO).

    Hier stehen zwei Pflichten gegeneinander: das Recht auf Löschung und die
    handels- und steuerrechtliche Aufbewahrungspflicht für Rechnungsdaten
    (§ 147 AO, § 257 HGB, in der Regel zehn Jahre). Art. 17 Abs. 3 lit. b
    DSGVO löst das: die Löschpflicht gilt nicht, soweit die Verarbeitung zur
    Erfüllung einer rechtlichen Verpflichtung erforderlich ist.

    Umgesetzt heißt das:

    - Das Konto selbst wird gelöscht. Über die Fremdschlüssel verschwinden
      damit auch Merkzettel, Warenkörbe und verknüpfte Social-Logins.
    - Bestellungen bleiben bestehen. Ihr `user_id` wird durch den
      Fremdschlüssel auf NULL gesetzt, die Rechnungsdaten (Name, Anschrift)
      bleiben als Momentaufnahme erhalten - sie SIND die aufzubewahrende
      Rechnung.

    Die Bestellungen lassen sich danach nicht mehr über das Konto einer
    Person zuordnen, sondern nur noch über die Rechnung selbst. Genau das
    ist gewollt.
    """
    if user is None:
        return _login_redirect(request)

    # Absichtsnachweis: ein versehentlicher Klick darf kein Konto löschen.
    if bestaetigung.strip().upper() != "LÖSCHEN":
        context = await _account_context(
            request, db, user, delete_error="Bitte zur Bestätigung das Wort LÖSCHEN eingeben."
        )
        return templates.TemplateResponse(request, "account.html", context, status_code=400)

    await db.delete(user)
    await db.commit()

    # Sitzungscookie mit entfernen - sonst zeigt der Browser weiter auf ein
    # Konto, das es nicht mehr gibt.
    response = await cookie_backend.transport.get_logout_response()
    response.status_code = status.HTTP_303_SEE_OTHER
    response.headers["location"] = "/?geloescht=1"
    return response


@router.get("")
async def account_home(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(current_user_optional),
):
    if user is None:
        return _login_redirect(request)

    context = await _account_context(request, db, user)
    return templates.TemplateResponse(request, "account.html", context)


@router.post("/wishlist/{product_id}")
async def add_to_wishlist(
    product_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(current_user_optional),
):
    if user is None:
        return _login_redirect(request)

    existing = await db.execute(
        select(WishlistItem).where(WishlistItem.user_id == user.id, WishlistItem.product_id == product_id)
    )
    if existing.scalar_one_or_none() is None:
        db.add(WishlistItem(user_id=user.id, product_id=product_id))
        await db.commit()

    redirect_to = _safe_referer_path(request.headers.get("referer", ""))
    return RedirectResponse(url=redirect_to, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/wishlist/{product_id}/remove")
async def remove_from_wishlist(
    product_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(current_user_optional),
):
    if user is None:
        return _login_redirect(request)

    result = await db.execute(
        select(WishlistItem).where(WishlistItem.user_id == user.id, WishlistItem.product_id == product_id)
    )
    item = result.scalar_one_or_none()
    if item is not None:
        await db.delete(item)
        await db.commit()

    redirect_to = _safe_referer_path(request.headers.get("referer", ""))
    return RedirectResponse(url=redirect_to, status_code=status.HTTP_303_SEE_OTHER)
