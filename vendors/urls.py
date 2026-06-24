from django.urls import path
from . import views

urlpatterns = [
    path('', views.vendor_list, name='vendor_list'),
    path('add/', views.add_vendor, name='add_vendor'),
    path('edit/<int:vendor_id>/', views.edit_vendor, name='edit_vendor'),
    path('delete/<int:vendor_id>/', views.delete_vendor, name='delete_vendor'),
]