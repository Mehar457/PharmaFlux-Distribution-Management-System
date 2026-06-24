from django.urls import path
from . import views

urlpatterns = [
    path('sales/', views.sale_report, name='sale_report'),
    path('purchases/', views.purchase_report, name='purchase_report'),
    path('profit-loss/', views.profit_loss_report, name='profit_loss_report'),
]