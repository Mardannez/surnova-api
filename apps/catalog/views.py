import django_filters
from django.db.models import Exists, Min, OuterRef, Prefetch, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, viewsets
from rest_framework.permissions import AllowAny

from .models import Brand, Category, Product, ProductImage, ProductVariant
from .serializers import BrandSerializer, CategorySerializer, ProductSerializer


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"


class BrandViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Brand.objects.filter(is_active=True)
    serializer_class = BrandSerializer
    permission_classes = [AllowAny]


class ProductFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name="category__slug")
    brand = django_filters.CharFilter(field_name="brand__slug")
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = Product
        fields = ["category", "brand", "featured"]


class ProductSearchFilter(filters.SearchFilter):
    def filter_queryset(self, request, queryset, view):
        for term in self.get_search_terms(request):
            active_sku = ProductVariant.objects.filter(
                product_id=OuterRef("pk"), is_active=True, sku__icontains=term
            )
            queryset = queryset.filter(
                Q(name__icontains=term)
                | Q(short_description__icontains=term)
                | Q(description__icontains=term)
                | Q(Exists(active_sku))
            )
        return queryset


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, ProductSearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ["name", "short_description", "description", "variants__sku"]
    ordering_fields = ["price", "name", "created_at"]
    ordering = ["-created_at", "id"]

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True, category__is_active=True)
            .filter(Q(brand__isnull=True) | Q(brand__is_active=True))
            .annotate(price=Min("variants__price", filter=Q(variants__is_active=True)))
            .filter(price__isnull=False)
            .select_related("category", "brand")
            .prefetch_related(
                Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True)),
                Prefetch(
                    "images",
                    queryset=ProductImage.objects.filter(
                        Q(variant__isnull=True) | Q(variant__is_active=True)
                    ),
                ),
            )
        )
