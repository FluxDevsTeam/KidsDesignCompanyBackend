from decimal import Decimal

from django.db import models
from workers.models import Contractors, SalaryWorkers
from project.models import Project
from django.core.validators import MinValueValidator, MaxValueValidator
import project.utils as p


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

    @property
    def total_raw_material_cost(self):
        from django.db.models import Sum, F, ExpressionWrapper
        from django.db.models.functions import Coalesce
        from store.models import Removed
        from django.db.models import Sum, F, ExpressionWrapper, DecimalField
        raw_materials = Removed.objects.filter(product=self).annotate(
            total_cost=ExpressionWrapper(
                F("quantity") * F("material__price"),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ).aggregate(total=Coalesce(Sum("total_cost"), Decimal(0)))
        return raw_materials['total']

    @property
    def total_artisan_cost(self):
        from django.db.models import Sum
        contractor_cost = ProductContractor.objects.filter(product=self).aggregate(total=Sum("cost"))["total"] or 0
        return round(contractor_cost)

    @property
    def total_production_cost(self):
        return round(self.total_artisan_cost + self.total_raw_material_cost)

    @property
    def grand_total(self):
        calculated_overhead = self.overhead_cost * self.overhead_cost_base_at_creation
        return round(calculated_overhead + self.total_production_cost)

    @property
    def grand_total_per_item(self):
        if self.quantity == 0:
            return 0
        calculated_overhead = self.overhead_cost * self.overhead_cost_base_at_creation
        return round((calculated_overhead + self.total_production_cost) / self.quantity)

    @property
    def profit(self):
        return round((self.selling_price * self.quantity) - self.grand_total)

    @property
    def profit_per_item(self):
        if self.quantity == 0:
            return 0
        return round(self.profit / self.quantity)

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

    def __str__(self):
        return f"{self.contractor.name} for {self.product.name}"


class ProductSalaryWorker(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    salary_worker = models.ForeignKey(SalaryWorkers, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.salary_worker.name} for {self.product.name}"
