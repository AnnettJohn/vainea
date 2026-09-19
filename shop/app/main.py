from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.admin import register_admin
from app.core.config import get_settings
from app.core.users import auth_backend, fastapi_users
from app.db.session import engine
from app.routers import account, cart, checkout, home, legal, products, seo, shop, states, story
from app.schemas.user import UserCreate, UserRead, UserUpdate

settings = get_settings()

app = FastAPI(title="VAINEA")

app.add_middleware(SessionMiddleware, secret_key=settings.admin_session_secret)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Öffentliche Seiten (serverseitig gerendert, HTMX-Fragmente über HX-Request-Header)
app.include_router(home.router)
app.include_router(states.router)
app.include_router(shop.router)
app.include_router(products.router)
app.include_router(story.router)
app.include_router(cart.router)
app.include_router(checkout.router)
app.include_router(account.router)
app.include_router(legal.router)
app.include_router(seo.router)

# FastAPI-Users: Auth/Registrierung/Nutzerverwaltung
app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"])
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"])

register_admin(app, engine)
