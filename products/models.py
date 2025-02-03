from django.db import models
from workers.models import Contractors, SalaryWorkers
from project.models import Project


class Product(models.Model):
    # project = models.ForeignKey(Project, on_delete=models.PROTECT)
    # quantity = models.IntegerField(default=1)
    name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    images = models.ImageField(upload_to="product/", blank=True, null=True)
    dimensions = models.CharField(max_length=50)
    colour = models.CharField(max_length=50)
    design = models.TextField()
    # contractors = models.ManyToManyField(Contractors, through='ProductContractor')
    # salary_workers = models.ManyToManyField(SalaryWorkers, through='ProductSalaryWorker')
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    overhead_cost = models.DecimalField(max_digits=10, decimal_places=2)
    production_note = models.TextField()

    @property
    def total_production_cost(self):
        total_cost = 5

        return total_cost

    @property
    def total_artisan_cost(self):
        total_cost = 0
        total_cost += int(sum([pc.cost for pc in self.productcontractor_set.all()]))
        total_cost += sum([psw.cost for psw in self.productsalaryworker_set.all()])
        return total_cost

    @property
    def profit(self):
        return (self.selling_price - self.total_production_cost) * self.quantity

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


class ProductContractor(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    contractor = models.ForeignKey(Contractors, on_delete=models.PROTECT)
    cost = models.DecimalField(max_digits=10, decimal_places=2)  # Individual pay

    def __str__(self):
        return f"{self.contractor.name} for {self.product.name}"


class ProductSalaryWorker(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    salary_worker = models.ForeignKey(SalaryWorkers, on_delete=models.PROTECT)
    cost = models.DecimalField(max_digits=10, decimal_places=2)  # Individual pay

    def __str__(self):
        return f"{self.salary_worker.name} for {self.product.name}"
