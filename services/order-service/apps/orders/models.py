from django.db import models

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    user_id = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.TextField()
    user_email = models.EmailField(blank=True)
    user_name = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.id} by User {self.user_id}"

    @property
    def items_count(self):
        """Вычисляет общее количество товаров в заказе."""
        return self.items.count()

    @property
    def total_quantity(self):
        """Вычисляет общее количество единиц товаров в заказе."""
        return sum(item.quantity for item in self.items.all())

    def calcilate_total(self):
        """Вычисляет общую сумму заказа на основе его элементов."""
        total = sum(item.subtotal for item in self.items.all())
        self.total_amount = total
        return total


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_id = models.IntegerField()
    product_name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity} x {self.product_name or f'Product {self.product_id}'}"

    @property
    def subtotal(self):
        """Вычисляет подитог для данного элемента заказа."""
        return self.price * self.quantity



