from django.urls import path
from . import views

urlpatterns = [
    path('', views.sale_list, name='sale_list'),
    path('add/', views.add_sale, name='add_sale'),
    path('invoice/<int:sale_id>/', views.view_invoice, name='view_invoice'),
]