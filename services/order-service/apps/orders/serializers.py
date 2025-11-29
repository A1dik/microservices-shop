from rest_framework import serializers
from .models import Order, OrderItem

class OrderItemSerializer(serializers.ModelSerializer):
    """Сериализатор для элемента заказа."""
    Subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product_id',
            'product_name',
            'quantity',
            'price',
            'subtotal',
            'created_at',
        ]

class OrderSerializer(serializers.ModelSerializer):
    """Сериализатор для заказа."""
    items = OrderItemSerializer(many=True, read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    total_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'user_id',
            'status',
            'total_amount',
            'items_count',
            'total_quantity',
            'shipping_address',
            'created_at',
            'updated_at',
            'items',
        ]
        read_only_fields = ['user_id', 'total_amount', 'user_email', 'user_name']

class CreateOrderSerializer(serializers.Serializer):
    """Сериализатор для создания заказа."""
    shipping_address = serializers.CharField(max_length=500)

    def validate_shipping_address(self, value):
        """Проверяет корректность адреса доставки."""
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Адрес доставки не может быть пустым.")
        return value


class UpdateOrderStatusSerializer(serializers.Serializer):
    """Сериализатор для обновления статуса заказа."""
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)

    def validate_status(self, value):
        """Проверяет корректность статуса заказа."""
        if value not in dict(Order.STATUS_CHOICES):
            raise serializers.ValidationError("Недопустимый статус заказа.")
        return value