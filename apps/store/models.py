from django.core.validators import MinValueValidator
from django.db import models
from apps.products.models import Product
from datetime import date


class StoreCategory(models.Model):
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return f"{self.name}"


class RawMaterial(models.Model):
    name = models.CharField(max_length=100, unique=True)
    unit = models.CharField(max_length=20)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(StoreCategory, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="raw_materials/", blank=True, null=True)
    archived = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Removed(models.Model):
    material = models.ForeignKey(RawMaterial, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=50)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    date = models.DateField(default=date.today)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.material} - {self.quantity}"


class AddRawMaterials(models.Model):
    item = models.ForeignKey(RawMaterial, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0.01)])
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(default=date.today)

    def __str__(self):
        return f"added {self.quantity} {self.item.name}"
