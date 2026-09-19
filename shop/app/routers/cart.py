import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.cart import (
    CART_COOKIE_MAX_AGE,
    CART_COOKIE_NAME,
    cart_count,
    cart_subtotal,
    get_cart_by_id,
    get_cart_if_exists,
    get_or_create_cart,
    get_owned_cart_item,
)
from app.core.context import get_base_context
from app.core.templates import templates
from app.db.session import get_db
from app.models.cart import CartItem
from app.models.product import ProductSize

router = APIRouter()


@router.get("/cart")
async def view_cart(
    request: Request, db: AsyncSession = Depends(get_db), base_context: dict = Depends(get_base_context)
):
    cart = await get_cart_if_exists(request, db)
    context = {
        **base_context,
        "cart": cart,
        "subtotal": cart_subtotal(cart),
        "page_title": "Warenkorb — VAINEA",
    }
    return templates.TemplateResponse(request, "cart.html", context)


@router.post("/cart/items")
async def add_cart_item(
    request: Request,
    db: AsyncSession = Depends(get_db),
    product_size_id: uuid.UUID = Form(...),
    quantity: int = Form(1),
):
    size_result = await db.execute(
        select(ProductSize).options(selectinload(ProductSize.product)).where(ProductSize.id == product_size_id)
    )
    size = size_result.scalar_one_or_none()
    if size is None or size.stock <= 0:
        raise HTTPException(status_code=400, detail="Diese Größe ist gerade nicht verfügbar.")

    cart, new_token = await get_or_create_cart(request, db)

    existing = next((item for item in cart.items if item.product_size_id == size.id), None)
    if existing is not None:
        existing.quantity = min(existing.quantity + max(quantity, 1), size.stock)
    else:
        db.add(
            CartItem(
                cart_id=cart.id,
                product_id=size.product_id,
                product_size_id=size.id,
                quantity=min(max(quantity, 1), size.stock),
            )
        )
    await db.commit()

    cart = await get_cart_by_id(db, cart.id)
    response = templates.TemplateResponse(
        request,
        "partials/cart_toast.html",
        {
            "message": f"{size.product.name} ({size.size}) wurde in den Warenkorb gelegt.",
            "cart_count": cart_count(cart),
        },
    )
    if new_token:
        response.set_cookie(
            CART_COOKIE_NAME, new_token, max_age=CART_COOKIE_MAX_AGE, httponly=True, samesite="lax"
        )
    return response


@router.post("/cart/items/{item_id}/quantity")
async def update_cart_item_quantity(
    item_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    quantity: int = Form(...),
):
    item = await get_owned_cart_item(request, db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Position nicht gefunden.")

    size_result = await db.execute(select(ProductSize).where(ProductSize.id == item.product_size_id))
    size = size_result.scalar_one()
    item.quantity = max(1, min(quantity, size.stock))
    cart_id = item.cart_id
    await db.commit()

    cart = await get_cart_by_id(db, cart_id)
    return templates.TemplateResponse(
        request,
        "partials/cart_body_update.html",
        {"cart": cart, "subtotal": cart_subtotal(cart), "cart_count": cart_count(cart)},
    )


@router.post("/cart/items/{item_id}/remove")
async def remove_cart_item(item_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    item = await get_owned_cart_item(request, db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Position nicht gefunden.")

    cart_id = item.cart_id
    await db.delete(item)
    await db.commit()

    cart = await get_cart_by_id(db, cart_id)
    return templates.TemplateResponse(
        request,
        "partials/cart_body_update.html",
        {"cart": cart, "subtotal": cart_subtotal(cart), "cart_count": cart_count(cart)},
    )
