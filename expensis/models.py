from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum

from project.models import Project
from shop.models import Sold


class ExpenseCategory(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.name}"


class Expense(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True)
    project = models.ForeignKey(Project, on_delete=models.PROTECT, null=True, blank=True)
    shop = models.ForeignKey(Sold, on_delete=models.PROTECT, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.CharField(max_length=200)
    date = models.DateField(default=date.today)

    def __str__(self):
        return f"{self.description})"

    def clean(self):
        if self.project and self.shop:
            raise ValidationError("Expense cannot be associated with both a project and a shop item.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-date"]


class Assets(models.Model):
    name = models.CharField(max_length=50)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    expected_lifespan = models.CharField(max_length=50)
    is_still_available = models.BooleanField(default=True)
    date_added = models.DateField(default=date.today)
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} -- {self.value}"