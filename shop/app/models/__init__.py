"""Alle Modelle hier importieren, damit Base.metadata für Alembic vollständig ist."""

from app.models.cart import Cart, CartItem
from app.models.discount import DiscountCode, DiscountType
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product, ProductImage, ProductSize, ProductStatus
from app.models.shipping import ShippingRate, ShippingZone
from app.models.state import State
from app.models.user import OAuthAccount, User
from app.models.wishlist import WishlistItem

__all__ = [
    "Cart",
    "CartItem",
    "DiscountCode",
    "DiscountType",
    "Order",
    "OrderItem",
    "OrderStatus",
    "Product",
    "ProductImage",
    "ProductSize",
    "ProductStatus",
    "ShippingRate",
    "ShippingZone",
    "State",
    "OAuthAccount",
    "User",
    "WishlistItem",
]
