from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('superadmin/', views.superadmin_dashboard, name='superadmin_dashboard'),
    path('superadmin/add-distributor/', views.add_distributor, name='add_distributor'),
    path('superadmin/suspend/<int:dist_id>/', views.suspend_distributor, name='suspend_distributor'),
    path('superadmin/activate/<int:dist_id>/', views.activate_distributor, name='activate_distributor'),
    path('employees/', views.manage_employees, name='manage_employees'),
    path('employees/add/', views.add_employee, name='add_employee'),
]