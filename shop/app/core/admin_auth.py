from fastapi_users.password import PasswordHelper
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import select
from starlette.requests import Request

from app.db.session import async_session_maker
from app.models.user import User

_password_helper = PasswordHelper()


class AdminAuth(AuthenticationBackend):
    """Schützt /admin per Session-Login gegen User mit is_superuser=True.

    Nutzt denselben Passwort-Hash wie der reguläre FastAPI-Users-Login, es
    gibt also keinen separaten Admin-Account-Speicher.
    """

    async def login(self, request: Request) -> bool:
        form = await request.form()
        email = form.get("username")
        password = form.get("password")
        if not email or not password:
            return False

        async with async_session_maker() as session:
            result = await session.execute(select(User).where(User.email == email))
            user = result.unique().scalar_one_or_none()
            if user is None or not user.is_active or not user.is_superuser:
                return False
            verified, _ = _password_helper.verify_and_update(str(password), user.hashed_password)
            if not verified:
                return False

        request.session.update({"admin_user_email": email})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return bool(request.session.get("admin_user_email"))
