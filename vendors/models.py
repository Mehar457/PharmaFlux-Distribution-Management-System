from django.db import models
# Create your models here.
from users.models import Distributor
class Vendor(models.Model):
    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name='vendors'
    )
    company_name = models.CharField(
        max_length=200
    )
    contact = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.company_name