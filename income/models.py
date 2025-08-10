from decimal import Decimal
from django.db import models
from datetime import date


class Balance(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    cash = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0"))
    bank = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0"))
    debt = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0"))

    def __str__(self):
        return f"balance: {self.id}"


class IncomeCategory(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.name}"


class Income(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(IncomeCategory, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    cash = models.BooleanField(default=False)
    date = models.DateField(default=date.today)

    def __str__(self):
        return f"{self.name}"
