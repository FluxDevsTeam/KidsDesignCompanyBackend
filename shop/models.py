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
    category = models.ForeignKey(InventoryCategory, on_delete=models.SET_NULL, null=True, blank=True)
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
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    item = models.ForeignKey(InventoryItem, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=100)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0.01)])
    date = models.DateTimeField(auto_now_add=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    logistics = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    updated_on = models.DateTimeField(null=True, blank=True)

    @property
    def total_price(self):
        return round(self.quantity * self.selling_price)

    @property
    def profit(self):
        return (self.selling_price - self.cost_price) * self.quantity

    def clean(self):
        if self.project and self.logistics:
            raise ValueError("You can't set project and logistics value at the ame time. You can only set logistics value if the sold item is not to a project. ")

    def save(self, *args, **kwargs):
        if self.date:
            self.updated_on = now()
        # self.clean()

        super().save(*args, **kwargs)

    def __str__(self):
        try:
            return self.item.name
        except AttributeError:
            return self.name

    class Meta:
        ordering = ["-date"]


class AddStock(models.Model):
    item = models.ForeignKey(InventoryItem, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=100)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0.01)])
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"added {self.quantity} {self.item.name}"