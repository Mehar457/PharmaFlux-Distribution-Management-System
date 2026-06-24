from django.db import models
from users.models import Distributor

class Customer(models.Model):
    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name='customers'
    )
    name = models.CharField(max_length=200)
    type = models.CharField(
        max_length=100,
        blank=True
    )
    contact = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    whatsapp_number = models.CharField(
        max_length=20,
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name