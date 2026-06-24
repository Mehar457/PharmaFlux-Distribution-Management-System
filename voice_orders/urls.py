from django.urls import path
from . import views

urlpatterns = [
    path('',
         views.voice_orders_list,
         name='voice_orders_list'),
    path('webhook/',
         views.whatsapp_webhook,
         name='whatsapp_webhook'),
    path('create/',
         views.create_manual_voice_order,
         name='create_manual_voice_order'),
    path('confirm/<int:voice_order_id>/',
         views.confirm_order,
         name='confirm_order'),
    path('cancel/<int:voice_order_id>/',
         views.cancel_order,
         name='cancel_order'),
]