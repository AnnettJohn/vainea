from typing import Any

from mollie.api.client import Client as MollieClient
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings

settings = get_settings()


def mollie_configured() -> bool:
    return bool(settings.mollie_api_key)


def get_mollie_client() -> MollieClient:
    client = MollieClient()
    client.set_api_key(settings.mollie_api_key)
    return client


async def create_mollie_payment(client: MollieClient, data: dict[str, Any]) -> Any:
    """mollie-api-python ist synchron (nutzt requests) - Netzwerkaufrufe daher
    im Threadpool ausführen, um den Event-Loop nicht zu blockieren."""
    return await run_in_threadpool(client.payments.create, data)


async def get_mollie_payment(client: MollieClient, payment_id: str) -> Any:
    return await run_in_threadpool(client.payments.get, payment_id)
