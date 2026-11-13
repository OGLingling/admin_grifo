from django.contrib import admin

from .models import CashMovement, CashSession, Product, Purchase, Sale, Tank


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "category", "unit", "unit_price", "stock_quantity", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "sku")
    readonly_fields = ("stock_quantity", "created_at", "updated_at")


@admin.register(Tank)
class TankAdmin(admin.ModelAdmin):
    list_display = ("code", "product", "capacity", "current_stock", "warning_level", "is_active")
    list_filter = ("is_active",)
    readonly_fields = ("current_stock",)

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj:
            fields.append("product")
        return fields


class LedgerAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Purchase)
class PurchaseAdmin(LedgerAdmin):
    list_display = ("id", "product", "quantity", "unit_cost", "total", "supplier", "purchased_at")
    list_filter = ("purchased_at",)
    search_fields = ("supplier", "reference", "product__name")


@admin.register(Sale)
class SaleAdmin(LedgerAdmin):
    list_display = ("id", "product", "quantity", "total", "payment_method", "sold_at")
    list_filter = ("payment_method", "sold_at")
    search_fields = ("product__name",)


@admin.register(CashSession)
class CashSessionAdmin(LedgerAdmin):
    list_display = ("id", "opened_by", "opened_at", "opening_amount", "closed_at", "closing_amount")
    list_filter = ("opened_at", "closed_at")


@admin.register(CashMovement)
class CashMovementAdmin(LedgerAdmin):
    list_display = ("id", "cash_session", "direction", "description", "amount", "created_at")
    list_filter = ("direction", "created_at")
