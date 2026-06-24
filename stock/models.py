from django.db import models
# Create your models here.
from users.models import Distributor

class Stock(models.Model):
    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name='stocks'
    )
    medicine_name = models.CharField(
        max_length=200
    )
    batch_no = models.CharField(
        max_length=100,
        unique=True
    )
    quantity = models.IntegerField(default=0)
    expiry_date = models.DateField()
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    reorder_level = models.IntegerField(
        default=10
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.medicine_name

    def is_low_stock(self):
        return self.quantity <= self.reorder_level

    def is_expiring_soon(self):
        from datetime import date, timedelta
        return self.expiry_date <= (
            date.today() + timedelta(days=30)
        )