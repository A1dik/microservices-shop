from rest_framework import serializers
from .models import Cart, CartItem
from .services import ProductService

class CartItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    product_info = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            'id',
            'product_id',
            'product_name',
            'quantity',
            'price',
            'subtotal',
            'product_info',
            'created_at',
        ]

    def get_product_info(self, obj):
        """Получение информации о продукте из сервиса продуктов."""
        product_data = ProductService.get_product(obj.product_id)
        if product_data:
            return{
                'name': product_data.get('name'),
                'current_price': product_data.get('price'),
                'image_url': product_data.get('image_url'),
                'is_active': product_data.get('is_active'),
                'stock_quantity': product_data.get('stock_quantity'),
            }
        return None


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = [
            'id',
            'user_id',
            'items',
            'total_items',
            'total_amount',
            'created_at',
            'updated_at',
        ]

class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate_product_id(self, value):
        """Проверяет существует ли продукт и доступен ли он для добавления в корзину."""
        product_data = ProductService.get_product(value)
        if not product_data:
            raise serializers.ValidationError("Product does not exist.")
        if not product_data.get('is_active'):
            raise serializers.ValidationError("Product is not active.")
        return value


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
