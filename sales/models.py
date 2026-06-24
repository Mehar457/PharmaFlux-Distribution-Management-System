from django.db import models
# Create your models here.
from users.models import Distributor
from customers.models import Customer
from orders.models import Order

class Sale(models.Model):
    PAYMENT = [
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('credit', 'Credit'),
    ]
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='sale'
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='sales'
    )
    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name='sales'
    )
    sale_date = models.DateField(
        auto_now_add=True
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT,
        default='cash'
    )

    def __str__(self):
        return f"Sale #{self.id}"

class Invoice(models.Model):
    sale = models.OneToOneField(
        Sale,
        on_delete=models.CASCADE,
        related_name='invoice'
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE
    )
    invoice_date = models.DateTimeField(
        auto_now_add=True
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    contact = models.CharField(
        max_length=20,
        blank=True
    )

    def __str__(self):
        return f"Invoice #{self.id}"