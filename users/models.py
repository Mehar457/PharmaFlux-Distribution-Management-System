from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLES = [
        ('superadmin', 'Super Admin'),
        ('distributor', 'Distributor'),
        ('employee', 'Employee'),
    ]
    role = models.CharField(
        max_length=20,
        choices=ROLES,
        default='distributor'
    )


class Distributor(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='distributor'
    )
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        default='active'
    )

    def __str__(self):
        return self.name


class Employee(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='employee'
    )
    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name='employees'
    )
    name = models.CharField(max_length=200)
    privileges = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
