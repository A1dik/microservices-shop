from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Order, OrderItem
from .serializers import (
    OrderSerializer, CreateOrderSerializer,
    UpdateOrderStatusSerializer
)
from .services import CartService, ProductService, UserService, event_bus
import logging

logger = logging.getLogger(__name__)

class IsAuthenticatedCustom:
    """Пользователь должен быть аутентифицирован."""
    def has_permission(self, request, view):
        return hasattr(request, 'user_id') and request.user_id is not None


class OrderListView(generics.ListAPIView):
    """Список заказов пользователя."""
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticatedCustom]

    def get_queryset(self):
        return Order.objects.filter(user_id=self.request.user_id)


class OrderDetailView(generics.RetrieveAPIView):
    """Детали заказа."""
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticatedCustom]

    def get_object(self):
        return get_object_or_404(Order, id=self.kwargs['pk'], user_id=self.request.user_id)


@api_view(['POST'])
@permission_classes([IsAuthenticatedCustom])
def create_order(request):

    logger.info("Create order request received for user_id: %s", request.user_id)


    #извекаем данные из запроса
    shipping_adress = request.data.get('shipping_data', {})
    customer_info = request.data.get('customer_info', {})
    special_instructions = request.data.get('special_instructions', '')

    if not shipping_adress:
        return Response({'detail': 'Shipping address is required.'}, status=status.HTTP_400_BAD_REQUEST)

    user_id = request.user_id
    try:
        with transaction.atomic():
            # получаем корзину пользователя
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            cart_data = CartService.get_user_cart(user_id, token)

        if not cart_data or not cart_data.get('items'):
            logger.warning("Empty cart for user_id: %s", user_id)
            return Response({'detail': 'Cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)
        logger.info("Cart data retrieved for user_id: %s", user_id)

            # получаем данные пользователя
        user_data = UserService.get_user_from_token(token)
        if not user_data:
            logger.error("User data not found for user_id: %s", user_id)
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # подготавливаем данные для резервирования
        items_to_reserve = []
        for cart_item in cart_data['items']:
            items_to_reserve.append({
                'product_id': cart_item['product_id'],
                'quantity': cart_item['quantity']
            })

        #резервируем продукты
        logger.info("Reserving products for user_id: %s", user_id)
        if not ProductService.reserve_products(items_to_reserve):
            logger.error("Failed to reserve products for user_id: %s", user_id)
            return Response({'detail': 'Failed to reserve products.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_name = ''
            if customer_info:
                user_name = f"{customer_info.get('first_name', '')} {customer_info.get('last_name', '')}".strip()

            if not user_name:
                user_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()

            #создаем заказ
            order = Order.objects.create(
                user_id=user_id,
                user_email=customer_info.get('email', user_data.get('email', '')),
                user_name=user_name,
                shipping_address=shipping_adress,
                total_amount=cart_data['total_amount'],
            )
            logger.info("Order created with id %s for user_id: %s", order.id, user_id)

            # создаем позиции заказа
            order_items = []
            for cart_item in cart_data['items']:
                order_item = OrderItem(
                    order=order,
                    product_id=cart_item['product_id'],
                    product_name=cart_item['product_name'],
                    quantity=cart_item['quantity'],
                    price=cart_item['price']
                )
                order_items.append({
                    'product_id': order_item.product_id,
                    'product_name': order_item.product_name,
                    'quantity': order_item.quantity,
                    'price': float(order_item.price)
                })

            # сохраняем  специальные инструкции, если есть
            if special_instructions:
                order.shipping_address += f"\n\nSpecial Instructions: {special_instructions}"
                order.save()

            # отправляем событие о создании заказа

            event_bus.publish_event('order.created', {
                'order_id': order.id,
                'user_id': user_id,
                'items': order_items,
                'total_amount': float(order.total_amount),
                'customer_info': customer_info,
            })

            logger.info("Published order.created event for order_id: %s", order.id)

            return Response({
                'message': 'Order created successfully.',
                'order': OrderSerializer(order).data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error("Error creating order for user_id %s: %s", user_id, str(e))
            # отменяем резервирование продуктов в случае ошибки
            ProductService.release_products(items_to_reserve)
            raise

    except Exception as e:
        logger.error("Transaction error for user_id %s: %s", user_id, str(e))
        return Response({'detail': 'Error creating order.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['PUT'])
@permission_classes([IsAuthenticatedCustom])
def update_order_status(request, pk):
    """Обновление статуса заказа (только для администраторов)"""
    order = get_object_or_404(Order, id=pk)

    serializer = UpdateOrderStatusSerializer(data=request.data)
    if serializer.is_valid():
        old_status = order.status
        new_status = serializer.validated_data['status']

        # Проверяем валидность перехода статуса
        if not is_valid_status_transition(old_status, new_status):
            return Response({
                'error': f'Invalid status transition from {old_status} to {new_status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        order.status = new_status
        order.save()

        # Публикуем событие об изменении статуса
        event_bus.publish_event('order.status_changed', {
            'order_id': order.id,
            'user_id': order.user_id,
            'old_status': old_status,
            'new_status': new_status
        })

        # Если заказ отменен, освобождаем товары
        if new_status == 'cancelled':
            items_to_release = []
            for item in order.items.all():
                items_to_release.append({
                    'product_id': item.product_id,
                    'quantity': item.quantity
                })
            ProductService.release_products(items_to_release)

            event_bus.publish_event('order.cancelled', {
                'order_id': order.id,
                'user_id': order.user_id,
                'items': items_to_release
            })

        return Response(OrderSerializer(order).data)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def is_valid_status_transition(old_status: str, new_status: str) -> bool:
    """Проверка валидности перехода между статусами"""
    valid_transitions = {
        'pending': ['confirmed', 'cancelled'],
        'confirmed': ['shipped', 'cancelled'],
        'shipped': ['delivered', 'cancelled'],
        'delivered': [],  # Финальный статус
        'cancelled': []   # Финальный статус
    }

    return new_status in valid_transitions.get(old_status, [])

@api_view(['GET'])
@permission_classes([IsAuthenticatedCustom])
def order_statistics(request):
    """Статистика заказов пользователя"""
    user_id = request.user_id
    orders = Order.objects.filter(user_id=user_id)

    stats = {
        'total_orders': orders.count(),
        'pending_orders': orders.filter(status='pending').count(),
        'confirmed_orders': orders.filter(status='confirmed').count(),
        'shipped_orders': orders.filter(status='shipped').count(),
        'delivered_orders': orders.filter(status='delivered').count(),
        'cancelled_orders': orders.filter(status='cancelled').count(),
        'total_spent': sum(order.total_amount for order in orders if order.status != 'cancelled')
    }

    return Response(stats)


