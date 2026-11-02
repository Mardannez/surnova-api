from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog.models import Brand, Category, Product, ProductVariant
from apps.inventory.models import Inventory, InventoryMovement
from apps.inventory.services.inventory_service import move_stock
from apps.users.models import User
from config.settings.base import env


class Command(BaseCommand):
    help = (
        "Carga datos demo idempotentes sin reiniciar precios, existencias o contraseñas existentes."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        from django.conf import settings

        if settings.SETTINGS_MODULE == "config.settings.production":
            raise CommandError("seed_demo solo está habilitado para desarrollo/pruebas.")
        brand, _ = Brand.objects.get_or_create(slug="surnova", defaults={"name": "SURNOVA"})
        data = [
            (
                "ropa",
                "Ropa",
                "camiseta-surnova",
                "Camiseta SURNOVA",
                "SN-CAM-M",
                "Mediana / Azul",
                "350.00",
                {"talla": "M", "color": "azul"},
            ),
            (
                "ropa",
                "Ropa",
                "camiseta-surnova",
                "Camiseta SURNOVA",
                "SN-CAM-L",
                "Grande / Azul",
                "375.00",
                {"talla": "L", "color": "azul"},
            ),
            (
                "accesorios",
                "Accesorios",
                "mochila-surnova",
                "Mochila SURNOVA",
                "SN-MOC-NEG",
                "Negra",
                "890.00",
                {"color": "negro"},
            ),
        ]
        for category_slug, category_name, slug, name, sku, variant_name, price, attributes in data:
            category, _ = Category.objects.get_or_create(
                slug=category_slug, defaults={"name": category_name}
            )
            product, _ = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "category": category,
                    "brand": brand,
                    "description": f"{name} de demostración.",
                    "featured": True,
                },
            )
            variant, _ = ProductVariant.objects.get_or_create(
                sku=sku,
                defaults={
                    "product": product,
                    "name": variant_name,
                    "price": Decimal(price),
                    "attributes": attributes,
                },
            )
            _, created = Inventory.objects.get_or_create(variant=variant)
            if created:
                move_stock(
                    variant_id=variant.pk,
                    movement_type=InventoryMovement.Type.IN,
                    quantity=25,
                    reference="seed_demo",
                )
        email = env("DEMO_CUSTOMER_EMAIL", default="cliente@example.test").strip().lower()
        if not User.objects.filter(email__iexact=email).exists():
            password = env("DEMO_CUSTOMER_PASSWORD", default="")
            User.objects.create_user(
                email=email, password=password or None, first_name="Cliente", last_name="Demo"
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo disponible: 2 categorías, 1 marca, 2 productos, 3 variantes. Cliente: {email}"
            )
        )
        self.stdout.write(
            "Contraseña configurada por DEMO_CUSTOMER_PASSWORD al crear el usuario; si estaba vacía, usa changepassword. No se crean administradores ni se descargan imágenes."
        )
