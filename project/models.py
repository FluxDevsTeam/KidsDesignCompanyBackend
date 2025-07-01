from datetime import date
from django.db import models
from customers.models import Customer
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator


class Project(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    invoice_image = models.ImageField(upload_to="project_invoice/", blank=True, null=True)
    status = models.CharField(max_length=50, default="Not started")
    start_date = models.DateField(default=date.today)
    all_items = models.JSONField(blank=True, null=True)
    tasks = models.JSONField(blank=True, null=True)
    deadline = models.DateField(default=date.today, blank=True, null=True)
    progress = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)],help_text="Progress as a whole number percentage (0 to 100).")
    date_delivered = models.DateField(blank=True, null=True)
    is_delivered = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)
    selling_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    logistics = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    service_charge = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    note = models.TextField(null=True, blank=True)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    @property
    def timeframe(self):
        return (self.deadline - self.start_date).days if self.deadline else None

    @property
    def paid(self):
        return self.selling_price + self.logistics + self.service_charge

    def __str__(self):
        return f"Project {self.name}"

    class Meta:
        ordering = ["deadline"]


class OverheadCost(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    overhead_cost_base = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("100000"))

    def __str__(self):
        return f"Overhead Cost Base: {self.overhead_cost_base}"


class OtherProduction(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    budget = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    cost = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.name

