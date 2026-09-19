from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqladmin.filters import AllUniqueStringValuesFilter, StaticValuesFilter
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.admin_auth import AdminAuth
from app.core.config import get_settings
from app.models.discount import DiscountCode
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product, ProductImage, ProductSize, ProductStatus
from app.models.shipping import ShippingRate, ShippingZone
from app.models.state import State

settings = get_settings()


class StateAdmin(ModelView, model=State):
    name = "State"
    name_plural = "States"
    icon = "fa-solid fa-palette"
    column_list = [State.id, State.slug, State.name, State.hex_color, State.sort_order]
    column_searchable_list = [State.name, State.slug]
    column_sortable_list = [State.sort_order, State.name]
    column_default_sort = [(State.sort_order, False)]
    form_columns = [
        State.slug,
        State.num,
        State.name,
        State.hex_color,
        State.mood_text,
        State.brand_line,
        State.story_text,
        State.hero_image_url,
        State.hero_image_position,
        State.circle_image_url,
        State.sort_order,
        State.meta_title,
        State.meta_description,
    ]


class ProductImageAdmin(ModelView, model=ProductImage):
    name = "Product Image"
    name_plural = "Product Images"
    icon = "fa-solid fa-image"
    column_list = [ProductImage.product, ProductImage.url, ProductImage.sort_order, ProductImage.alt_text]
    column_sortable_list = [ProductImage.sort_order]
    form_columns = [ProductImage.product, ProductImage.url, ProductImage.sort_order, ProductImage.alt_text]


class ProductSizeAdmin(ModelView, model=ProductSize):
    name = "Product Size"
    name_plural = "Product Sizes"
    icon = "fa-solid fa-ruler"
    column_list = [ProductSize.product, ProductSize.size, ProductSize.stock, ProductSize.sku]
    column_searchable_list = [ProductSize.sku]
    form_columns = [ProductSize.product, ProductSize.size, ProductSize.stock, ProductSize.sku]


class ProductAdmin(ModelView, model=Product):
    """Bilder & Größen werden über die eigenen ProductImage-/ProductSize-Views
    gepflegt: SQLAdmin bietet (anders als Django-Admin) keine Inline-Formsets
    für verschachtelte Objekte, das FK-Auswahlfeld dort übernimmt die
    Zuordnung zum Produkt. Für ~24 Produkte laut Pflichtenheft ausreichend.
    """

    name = "Product"
    name_plural = "Products"
    icon = "fa-solid fa-shirt"
    column_list = [
        Product.name,
        Product.slug,
        Product.category,
        Product.state,
        Product.price,
        Product.status,
        Product.is_new,
        Product.is_bestseller,
    ]
    column_searchable_list = [Product.name, Product.slug, Product.category]
    column_sortable_list = [Product.name, Product.price, Product.category]
    column_filters = [
        AllUniqueStringValuesFilter(Product.category),
        StaticValuesFilter(Product.status, values=[(s.value, s.value) for s in ProductStatus]),
    ]
    form_columns = [
        Product.name,
        Product.slug,
        Product.description,
        Product.category,
        Product.state,
        Product.material,
        Product.price,
        Product.weight_grams,
        Product.is_new,
        Product.is_bestseller,
        Product.variant,
        Product.status,
        Product.product_group_id,
        Product.meta_title,
        Product.meta_description,
    ]


class OrderItemAdmin(ModelView, model=OrderItem):
    name = "Order Item"
    name_plural = "Order Items"
    icon = "fa-solid fa-list"
    column_list = [
        OrderItem.order,
        OrderItem.product_name,
        OrderItem.size,
        OrderItem.quantity,
        OrderItem.line_total,
    ]
    can_create = False
    can_edit = False


class OrderAdmin(ModelView, model=Order):
    """Bestellinhalte und -preise sind Schnappschüsse zum Bestellzeitpunkt und
    bleiben deshalb unveränderlich; im Admin ist nur der Status pflegbar.
    """

    name = "Order"
    name_plural = "Orders"
    icon = "fa-solid fa-receipt"
    column_list = [
        Order.order_number,
        Order.status,
        Order.guest_email,
        Order.total,
        Order.currency,
        Order.mollie_payment_id,
        Order.created_at,
    ]
    column_searchable_list = [Order.order_number, Order.guest_email, Order.mollie_payment_id]
    column_sortable_list = [Order.created_at, Order.total]
    column_default_sort = [(Order.created_at, True)]
    column_filters = [StaticValuesFilter(Order.status, values=[(s.value, s.value) for s in OrderStatus])]
    column_details_exclude_list = []
    form_columns = [Order.status, Order.mollie_payment_id]
    can_create = False
    can_delete = False


class DiscountCodeAdmin(ModelView, model=DiscountCode):
    name = "Discount Code"
    name_plural = "Discount Codes"
    icon = "fa-solid fa-tag"
    column_list = [
        DiscountCode.code,
        DiscountCode.type,
        DiscountCode.value,
        DiscountCode.valid_from,
        DiscountCode.valid_until,
        DiscountCode.usage_count,
        DiscountCode.usage_limit_total,
        DiscountCode.is_active,
    ]
    column_searchable_list = [DiscountCode.code]
    form_columns = [
        DiscountCode.code,
        DiscountCode.type,
        DiscountCode.value,
        DiscountCode.valid_from,
        DiscountCode.valid_until,
        DiscountCode.usage_limit_total,
        DiscountCode.usage_limit_per_customer,
        DiscountCode.min_order_value,
        DiscountCode.is_active,
    ]


class ShippingZoneAdmin(ModelView, model=ShippingZone):
    """Nicht Teil der im Pflichtenheft genannten Kern-Admin-Modelle, aber
    nötig, damit die Platzhalter-Versandzonen (siehe scripts/seed.py) ohne
    Codeänderung durch echte Werte ersetzt werden können."""

    name = "Shipping Zone"
    name_plural = "Shipping Zones"
    icon = "fa-solid fa-truck"
    column_list = [ShippingZone.name, ShippingZone.country_codes, ShippingZone.free_shipping_threshold]
    form_columns = [ShippingZone.name, ShippingZone.country_codes, ShippingZone.free_shipping_threshold]


class ShippingRateAdmin(ModelView, model=ShippingRate):
    name = "Shipping Rate"
    name_plural = "Shipping Rates"
    icon = "fa-solid fa-money-bill"
    column_list = [ShippingRate.zone, ShippingRate.method_name, ShippingRate.price]
    form_columns = [ShippingRate.zone, ShippingRate.method_name, ShippingRate.price]


ADMIN_VIEWS: list[type[ModelView]] = [
    StateAdmin,
    ProductAdmin,
    ProductImageAdmin,
    ProductSizeAdmin,
    OrderAdmin,
    OrderItemAdmin,
    DiscountCodeAdmin,
    ShippingZoneAdmin,
    ShippingRateAdmin,
]


def register_admin(app: FastAPI, engine: AsyncEngine) -> Admin:
    admin = Admin(
        app,
        engine,
        authentication_backend=AdminAuth(secret_key=settings.admin_session_secret),
        base_url="/admin",
        title="VAINEA Admin",
    )
    for view in ADMIN_VIEWS:
        admin.add_view(view)
    return admin
