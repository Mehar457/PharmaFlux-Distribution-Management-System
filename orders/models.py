from django.db import models
from django.utils import timezone
# Create your models here.
from users.models import Distributor
from customers.models import Customer
from stock.models import Stock

class Order(models.Model):
    STATUS = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]
    TYPE = [
        ('manual', 'Manual'),
        ('voice', 'Voice'),
    ]
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    order_date = models.DateTimeField(
        default=timezone.now
    )
    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default='draft'
    )
    order_type = models.CharField(
        max_length=20,
        choices=TYPE,
        default='manual'
    )

    def __str__(self):
        return f"Order #{self.id}"

    def get_subtotal_total(self):
        return sum(
            item.get_subtotal()
            for item in self.items.all()
        )

    def get_total(self):
        total = self.get_subtotal_total() - self.discount
        return max(total, 0)


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE
    )
    quantity = models.IntegerField()
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def get_subtotal(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"Item #{self.id}"