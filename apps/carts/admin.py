from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Cart, CartItem


class CartItemInline(TabularInline):
    model = CartItem
    extra = 0
    can_delete = False
    readonly_fields = ["variant", "quantity", "created_at", "updated_at"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Cart)
class CartAdmin(ModelAdmin):
    list_display = ["id", "user", "status", "updated_at"]
    list_filter = ["status"]
    search_fields = ["user__email", "id"]
    readonly_fields = ["id", "user", "status", "created_at", "updated_at"]
    fields = readonly_fields
    inlines = [CartItemInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
