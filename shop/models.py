from django.core.validators import MinValueValidator
from django.db import models
from customers.models import Customer
from django.utils.timezone import now

from project.models import Project


class InventoryCategory(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.name}"


class InventoryItem(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(InventoryCategory, on_delete=models.PROTECT, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="shop/", blank=True, null=True)
    stock = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0.01)])
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    dimensions = models.CharField(max_length=100)
    archived = models.BooleanField(default=False)

    @property
    def total_price(self):
        return self.stock * self.selling_price

    @property
    def profit_per_item(self):
        return self.selling_price - self.cost_price

    def __str__(self):
        return self.name


class Sold(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    project = models.ForeignKey(Project, on_delete=models.PROTECT, null=True, blank=True)
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0.01)])
    date = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(null=True, blank=True)

    @property
    def total_price(self):
        return self.quantity * self.item.selling_price

    @property
    def profit(self):
        return (self.item.selling_price - self.item.cost_price) * self.quantity

    def save(self, *args, **kwargs):
        if self.date:
            self.updated_on = now()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-date"]


class AddStock(models.Model):
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0.01)])
    date = models.DateTimeField(auto_now_add=True)
