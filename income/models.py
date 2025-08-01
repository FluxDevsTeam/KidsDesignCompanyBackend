from django.db import models
from datetime import date


class IncomeCategory(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.name}"


class Income(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(IncomeCategory, on_delete=models.SET_NULL, null=True, Blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    cash = models.BooleanField(default=False)
    date = models.DateField(default=date.today)

    def __str__(self):
        return f"{self.name}"
