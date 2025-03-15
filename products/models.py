from decimal import Decimal

from django.db import models
from workers.models import Contractors, SalaryWorkers
from project.models import Project
from django.core.validators import MinValueValidator, MaxValueValidator
import project.utils as p
from datetime import date


class Product(models.Model):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, null=True, blank=True)
    name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)
    images = models.ImageField(upload_to="product/", blank=True, null=True)
    sketch = models.ImageField(upload_to="product/sketch/", blank=True, null=True)
    dimensions = models.CharField(max_length=50)
    colour = models.CharField(max_length=50)
    design = models.TextField(null=True, blank=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    overhead_cost = models.DecimalField(max_digits=10, decimal_places=2)
    overhead_cost_base_at_creation = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    progress = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)], help_text="Progress as a whole number percentage (0 to 100).")
    production_note = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.overhead_cost_base_at_creation is None:
            self.overhead_cost_base_at_creation = p.get_overhead_cost_instance()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["progress"]


class Quotation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    department = models.CharField(max_length=100)
    contractor = models.ManyToManyField(Contractors, related_name='quotations', blank=True)
    salary_worker = models.ManyToManyField(SalaryWorkers, related_name='quotations', blank=True)
    quotation = models.JSONField(default=list)

    def __str__(self):
        return f"quotation for - {self.product.name}"


class ProductContractor(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    contractor = models.ForeignKey(Contractors, on_delete=models.PROTECT)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(default=date.today, null=True, blank=True)

    def __str__(self):
        return f"{self.contractor.name} for {self.product.name}"


class ProductSalaryWorker(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    salary_worker = models.ForeignKey(SalaryWorkers, on_delete=models.PROTECT)
    date = models.DateField(default=date.today, null=True, blank=True)

    def __str__(self):
        return f"{self.salary_worker.name} for {self.product.name}"
