from django.db import models
from customers.models import Customer
from products.models import Product
from shop.models import InventoryItem


class Project(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    products = models.ManyToManyField(Product, related_name="projects")
    shop_items = models.ManyToManyField(InventoryItem, related_name="shop")
    invoice_image = models.ImageField(upload_to="project_invoice/", blank=True, null=True)
    status = models.CharField(max_length=50)
    start_date = models.DateField()
    deadline = models.DateField()
    running_expenses = models.DecimalField(max_digits=10, decimal_places=2)
    other_expensis = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def timeframe(self):
        return (self.deadline - self.start_date).days

    def total_cost(self):
        return sum(self.products.total_production_cost) + sum(self.shop_items.selling_price) + self.running_expenses + self.other_expensis

    def __str__(self):
        return f"Project for {self.customer} )"

    class Meta:
        ordering = ["deadline"]

