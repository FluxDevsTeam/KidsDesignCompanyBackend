import datetime

from django.db import models
from customers.models import Customer
from decimal import Decimal


class Project(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    invoice_image = models.ImageField(upload_to="project_invoice/", blank=True, null=True)
    status = models.CharField(max_length=50, default="Not started")
    start_date = models.DateField(default=datetime.date.today)
    deadline = models.DateField(blank=True, null=True)
    date_delivered = models.DateField(blank=True, null=True)
    other_expensis = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_delivered = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)

    @property
    def timeframe(self):
        return (self.deadline - self.start_date).days

    def total_cost(self):
        return sum(self.products.total_production_cost) + sum(self.shop_items.selling_price) + self.running_expenses + self.other_expensis

    def __str__(self):
        return f"Project for {self.customer} )"

    class Meta:
        ordering = ["deadline"]


class OverheadCost(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    overhead_cost_base = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("100000"))

    def __str__(self):
        return f"Overhead Cost Base: {self.overhead_cost_base}"
