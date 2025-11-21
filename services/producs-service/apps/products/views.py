from django.shortcuts import render
from rest_framework.views import status
from rest_framework import generics
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q
from .models import Product, Category
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import (
    ProductSerializer,
    ProductDetailSerializer,
    ProductCreateUpdateSerializer,
    CategorySerializer,
)


class CategoryListView(generics.ListAPIView):
    """Представление для получения списка категорий."""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [SearchFilter]
    search_fields = ['name', 'description']

class CategoryDetailView(generics.RetrieveAPIView):
    """Представление для получения детальной информации о категории."""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'

class ProductListView(generics.ListCreateAPIView):
    """Представление для получения списка продуктов и создания нового продукта."""
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price', 'created_at']
    ordering = ['created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Фильтрация по диапазону цен
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')

        if min_price :
            queryset = queryset.filter(price__gte=min_price)

        if max_price :
            queryset = queryset.filter(price__lte=max_price)

        # Фильтрация по наличию на складе
        in_stock = self.request.query_params.get('in_stock')
        if in_stock and in_stock.lower() == 'true':
            queryset = queryset.filter(stock_quantity__gt=0)

        return queryset

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductCreateUpdateSerializer
        return ProductSerializer

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProductCreateUpdateSerializer
        return ProductDetailSerializer

@api_view(['POST'])
def reserve_product(request, product_id):
    """Представление для резервирования определенного количества продукта."""
    try:
        product = Product.objects.get(id=product_id)
        quantity = request.data.get('quantity', 1)

        if product.reserve_quantity(quantity):
            """Успешное резервирование."""
            return Response({'message': 'Product reserved successfully.'}, status=status.HTTP_200_OK)
        else:
            """Недостаточно товара на складе."""
            return Response({'error': 'Insufficient stock quantity.'}, status=status.HTTP_400_BAD_REQUEST)

    except Product.DoesNotExist:
        return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def release_product(request, product_id):
    """Представление для освобождения определенного количества продукта."""
    try:
        product = Product.objects.get(id=product_id)
        quantity = request.data.get('quantity', 1)

        product.release_quantity(quantity)
        return Response({'message': 'Product released successfully.'}, status=status.HTTP_200_OK)

    except Product.DoesNotExist:
        return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def check_availability(request, product_id):
    """Представление для проверки доступности продукта."""
    try:
        product = Product.objects.get(id=product_id)
        quantity = request.query_params.get('quantity', 1)

        return Response({
            'product_id': product.id,
            'name': product.name,
            'price': str(product.price),
            'available': product.stock_quantity >= quantity,
            'stock_quantity': product.stock_quantity,
            'requested_quantity': quantity,
        })

    except Product.DoesNotExist:
        return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
