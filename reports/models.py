from django.db import models
# Create your models here.
from users.models import Distributor
from customers.models import Customer
from vendors.models import Vendor

class Report(models.Model):
    TYPES = [
        ('sale', 'Sale Report'),
        ('purchase', 'Purchase Report'),
        ('profit_loss', 'Profit Loss Report'),
    ]
    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name='reports'
    )
    report_type = models.CharField(
        max_length=20,
        choices=TYPES
    )
    start_date = models.DateField()
    end_date = models.DateField()
    generated_at = models.DateTimeField(
        auto_now_add=True
    )
    generated_by = models.CharField(
        max_length=100,
        blank=True
    )

    def __str__(self):
        return f"Report #{self.id} - {self.report_type}"

class SaleReport(models.Model):
    report = models.OneToOneField(
        Report,
        on_delete=models.CASCADE,
        related_name='sale_report'
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    total_sale_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    def __str__(self):
        return f"Sale Report #{self.id}"

class PurchaseReport(models.Model):
    report = models.OneToOneField(
        Report,
        on_delete=models.CASCADE,
        related_name='purchase_report'
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    total_purchase_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    def __str__(self):
        return f"Purchase Report #{self.id}"

class ProfitLossReport(models.Model):
    report = models.OneToOneField(
        Report,
        on_delete=models.CASCADE,
        related_name='profit_loss_report'
    )
    total_sales = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    total_purchases = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    net_profit_loss = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    def __str__(self):
        return f"P&L Report #{self.id}"