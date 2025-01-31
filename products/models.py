from django.db import models
from workers.models import Contractors, SalaryWorkers

class Product(models.Model):
    name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    images = models.ImageField(upload_to="product/", blank=True, null=True)
    dimensions = models.CharField(max_length=50)
    colour = models.CharField(max_length=50)
    design = models.TextField()
    contractor = models.ForeignKey(Contractors, on_delete=models.PROTECT)
    contractor_cost = models.DecimalField(max_digits=10, decimal_places=2)
    salary_worker = models.ForeignKey(SalaryWorkers, on_delete=models.PROTECT)
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


class Quotation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    department = models.CharField(max_length=100)
    contractor = models.ManyToManyField(Contractors, related_name='quotations', blank=True)
    salary_worker = models.ManyToManyField(SalaryWorkers, related_name='quotations', blank=True)
    quotation = models.JSONField(default=list)

    def __str__(self):
        return f"quotation for - {self.product.name}"
