import datetime

from django.db import models
from customers.models import Customer
from django.core.validators import MinValueValidator, MaxValueValidator


class Project(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    invoice_image = models.ImageField(upload_to="project_invoice/", blank=True, null=True)
    status = models.CharField(max_length=50)
    start_date = models.DateField(default=datetime.date.today)
    deadline = models.DateField()
    date_delivered = models.DateField()
    other_expensis = models.DecimalField(max_digits=10, decimal_places=2)
    is_delivered = models.BooleanField(default=False)

    @property
    def timeframe(self):
        return (self.deadline - self.start_date).days

    def total_cost(self):
        return sum(self.products.total_production_cost) + sum(self.shop_items.selling_price) + self.running_expenses + self.other_expensis

    def __str__(self):
        return f"Project for {self.customer} )"

    class Meta:
        ordering = ["deadline"]

