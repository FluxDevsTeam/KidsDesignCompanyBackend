from django.db import models
from workers.models import Contractors, SalaryWorkers
import ast


class ListField(models.TextField):
    def to_python(self, value):
        if not value:
            return []
        if isinstance(value, list):
            return value
        return ast.literal_eval(value)

    def get_prep_value(self, value):
        if value is None:
            return value
        return ",".join(str(item) for item in value)


class Quotation(models.Model):
    name = models.CharField(max_length=100)
    quotation = ListField()

    def __str__(self):
        return self.name


class RawMaterialUsed(models.Model):
    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=20)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def cost_per_unit(self):
        return self.price / self.quantity

    category = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Product(models.Model):
    name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(max_length=10)
    raw_materials = models.ForeignKey(RawMaterialUsed, on_delete=models.PROTECT)
    images = models.ImageField(upload_to="product/", blank=True, null=True)
    quotation = models.ForeignKey(Quotation, on_delete=models.PROTECT)
    dimensions = models.CharField(max_length=50)
    colour = models.CharField(max_length=50)
    design = models.TextField()
    contractor = models.ForeignKey(Contractors, on_delete=models.PROTECT)
    contractor_cost = models.DecimalField(max_digits=10, decimal_places=2)
    salary_worker = models.ForeignKey(Contractors, on_delete=models.PROTECT)
    salary_worker_cost = models.DecimalField(max_digits=10, decimal_places=2)

    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)

    def total_production_cost(self):
        return self.cost_price + self.contractor_cost

    @property
    def profit(self):
        return (self.selling_price - self.cost_price) * self.quantity

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
