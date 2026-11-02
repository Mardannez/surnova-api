from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import F
from rest_framework.exceptions import APIException
from unfold.admin import ModelAdmin

from .models import Inventory, InventoryMovement
from .services.inventory_service import move_stock


class LowStockFilter(admin.SimpleListFilter):
    title = "Nivel de existencias"
    parameter_name = "low_stock"

    def lookups(self, request, model_admin):
        return [("yes", "Stock bajo"), ("no", "Por encima del mínimo")]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(quantity_available__lte=F("reorder_level"))
        if self.value() == "no":
            return queryset.filter(quantity_available__gt=F("reorder_level"))
        return queryset


@admin.register(Inventory)
class InventoryAdmin(ModelAdmin):
    list_display = [
        "variant",
        "quantity_available",
        "quantity_reserved",
        "reorder_level",
        "updated_at",
    ]
    search_fields = ["variant__sku", "variant__product__name"]
    readonly_fields = ["id", "quantity_available", "quantity_reserved", "updated_at"]
    autocomplete_fields = ["variant"]
    list_filter = [LowStockFilter]
    list_select_related = ["variant__product"]

    def get_readonly_fields(self, request, obj=None):
        return [*self.readonly_fields, "variant"] if obj else self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        return False


class MovementForm(forms.ModelForm):
    class Meta:
        model = InventoryMovement
        fields = ["variant", "movement_type", "quantity", "reference", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "movement_type" in self.fields:
            self.fields["movement_type"].choices = [
                (value, label)
                for value, label in InventoryMovement.Type.choices
                if value in {"IN", "OUT", "ADJUSTMENT"}
            ]

    def clean(self):
        data = super().clean()
        qty = data.get("quantity", 0)
        if qty == 0 or (data.get("movement_type") != "ADJUSTMENT" and qty < 0):
            raise ValidationError(
                "Cantidad inválida; ajustes permiten negativos, entradas/salidas requieren positivos."
            )
        return data


@admin.register(InventoryMovement)
class MovementAdmin(ModelAdmin):
    form = MovementForm
    list_display = ["variant", "movement_type", "quantity", "reference", "created_by", "created_at"]
    list_filter = ["movement_type"]
    search_fields = ["variant__sku", "reference"]
    autocomplete_fields = ["variant"]
    readonly_fields = ["created_by", "created_at", "id"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        stock = move_stock(
            variant_id=obj.variant_id,
            movement_type=obj.movement_type,
            quantity=obj.quantity,
            actor=request.user,
            reference=obj.reference,
            notes=obj.notes,
        )
        movement = stock.variant.inventory_movements.latest("created_at")
        obj.pk = movement.pk
        obj.created_by = request.user

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        try:
            return super().changeform_view(request, object_id, form_url, extra_context)
        except APIException as exc:
            # The enclosing admin transaction has rolled back before showing the form again.
            self.message_user(request, str(exc.detail), level=messages.ERROR)
            from django.shortcuts import redirect

            return redirect(request.path)
