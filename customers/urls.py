from django.urls import path
from . import views

urlpatterns = [
    path('', views.customer_list, name='customer_list'),
    path('add/', views.add_customer, name='add_customer'),
    path('edit/<int:customer_id>/', views.edit_customer, name='edit_customer'),
    path('delete/<int:customer_id>/', views.delete_customer, name='delete_customer'),
]