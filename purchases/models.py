from django.db import models
# Create your models here.
from users.models import Distributor
from vendors.models import Vendor
from stock.models import Stock

class Purchase(models.Model):
    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name='purchases'
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name='purchases'
    )
    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name='purchases'
    )
    purchase_date = models.DateField(
        auto_now_add=True
    )
    quantity = models.IntegerField()
    purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return f"Purchase #{self.id}"