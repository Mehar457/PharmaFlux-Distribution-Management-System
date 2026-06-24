from django.db import models
# Create your models here.
from users.models import Distributor
from orders.models import Order

class VoiceOrder(models.Model):
    STATUS = [
        ('processing', 'Processing'),
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='voice_order'
    )
    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name='voice_orders'
    )
    voice_input = models.TextField()
    converted_text = models.TextField(
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default='processing'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Voice Order #{self.id}"