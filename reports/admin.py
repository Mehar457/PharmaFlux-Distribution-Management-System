from django.contrib import admin
from .models import Report, SaleReport
from .models import PurchaseReport, ProfitLossReport
admin.site.register(Report)
admin.site.register(SaleReport)
admin.site.register(PurchaseReport)
admin.site.register(ProfitLossReport)