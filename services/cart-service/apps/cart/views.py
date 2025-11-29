from venv import create

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer, AddToCartSerializer, UpdateCartItemSerializer
from .services import ProductService
import logging

logger = logging.getLogger(__name__)
class IsAuthenticatedCustom:
    """Пользователь должен быть аутентифицирован."""
    def has_permission(self, request, view):
        return hasattr(request, 'user_id') and request.user_id is not None

class CartView(generics.RetrieveAPIView):
    """Представление для получения корзины пользователя."""
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticatedCustom]

    def get_object(self):
        logging.info("Fetching cart for user_id: %s", self.request.user_id)
        cart, created = Cart.objects.get_or_create(user_id=self.request.user_id)
        if created :
            logging.info("Created new cart for user_id: %s", self.request.user_id)
        return cart


@api_view(['POST'])
@permission_classes([IsAuthenticatedCustom])
def add_to_cart(request):
    """Представление для добавления товара в корзину."""
    logger.info("Add to cart request received for user_id: %s", request.user_id)

    serializer = AddToCartSerializer(data=request.data)
    if serializer.is_valid():
        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']

        #получаем корзину пользователя
        cart, create = Cart.objects.get_or_create(user_id=request.user_id)
        logger.info("Cart fetched/created for user_id: %s", request.user_id)

        #проверяем наличие продукта
        if not ProductService.check_availability(product_id, quantity):
            logger.warning("Product %s not available in requested quantity %s", product_id, quantity)
            return Response({'detail': 'Product not available in requested quantity.'}, status=status.HTTP_400_BAD_REQUEST)

        product_data = ProductService.get_product(product_id)
        if not product_data:
            logger.error("Product %s not found in ProductService", product_id)
            return Response({'detail': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

        #Добавляем или обновляем товар в корзине
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product_id=product_id,
            defaults={
                'product_name': product_data['name'],
                'price': product_data['price'],
                'quantity': quantity
            }
        )

        if not created:
            new_quantity = cart_item.quantity + quantity
            if not ProductService.check_availability(product_id, new_quantity):
                logger.warning("Product %s not available for updated quantity %s", product_id, new_quantity)
                return Response({'detail': 'Product not available in requested quantity.'}, status=status.HTTP_400_BAD_REQUEST)
            cart_item.quantity = new_quantity
            cart_item.save()
            logger.info("Updated quantity for product %s in cart", product_id)
        else:
            logger.info("Added product %s to cart", product_id)

        return Response({
            'message': 'Product added to cart successfully.',
            'cart_item': CartItemSerializer(cart_item).data
        }, status=status.HTTP_201_CREATED)

    logger.error(f"Add to cart validation errors: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['PUT'])
@permission_classes([IsAuthenticatedCustom])
def update_cart_item(request, item_id):
    """Представление для обновления количества товара в корзине."""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user_id=request.user_id)
    serializer = UpdateCartItemSerializer(data=request.data)
    if serializer.is_valid():
        new_quantity = serializer.validated_data['quantity']

        if not ProductService.check_availability(cart_item.product_id, new_quantity):
            return Response({'detail': 'Product not available in requested quantity.'}, status=status.HTTP_400_BAD_REQUEST)

        cart_item.quantity = new_quantity
        cart_item.save()

        return Response({
            'message': 'Cart item updated successfully.',
            'cart_item': CartItemSerializer(cart_item).data
        }, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticatedCustom])
def remove_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user_id=request.user_id)
    cart_item.delete()
    return Response({'message': 'Cart item deleted successfully.'}, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticatedCustom])
def clear_cart(request):
    try:
        cart = Cart.objects.get(user_id=request.user_id)
        cart.clear()
        return Response({'message': 'Cart cleared successfully.'}, status=status.HTTP_200_OK)
    except Cart.DoesNotExist:
        return Response({'detail': 'Cart not found.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticatedCustom])
def cart_summary(request):
    """Представление для получения сводки корзины пользователя."""
    try:
        cart = Cart.objects.get(user_id=request.user_id)
        return Response({
            'total_items': cart.total_items,
            'total_amount': cart.total_amount,
            'items_count': cart.items.count()
        })
    except Cart.DoesNotExist:
        return Response({
            'total_items': 0,
            'total_amount': 0,
            'items_count': 0
        })