from django.db import models
from decimal import Decimal


class Cart(models.Model):
    user_id = models.IntegerField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart of User {self.user_id}"

    @property
    def total_amount(self):
        """Вычисляет общую сумму корзины."""
        return sum(item.subtotal for item in self.items.all())

    @property
    def total_items(self):
        """Вычисляет общее количество товаров в корзине."""
        return sum(item.quantity for item in self.items.all())

    def clear(self):
        """Очищает корзину от всех товаров."""
        self.items.all().delete()
        self.save()


class CartItem(models.Model):
    """Элемент корзины, представляющий товар и его количество."""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product_id = models.IntegerField()
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    product_name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('cart', 'product_id')

    def __str__(self):
        return f"{self.quantity} x {self.product_name or f'Product {self.product_id}'}"

    @property
    def subtotal(self):
        """Вычисляет подитог для данного элемента корзины."""
        return self.price *  self.quantity


