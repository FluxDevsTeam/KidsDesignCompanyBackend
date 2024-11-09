from django.db import models
from products.models import Product


class Contractors(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    pay = models.DecimalField(max_digits=10, decimal_places=2)
    address = models.TextField(blank=True, null=True)
    craft_specialty = models.CharField(max_length=100, blank=True, null=True)
    years_of_experience = models.PositiveIntegerField(blank=True, null=True)
    image = models.ImageField(blank=True, null=True)
    date_joined = models.DateField(auto_now_add=True)
    date_left = models.DateField(auto_now_add=True)
    guarantor_name = models.CharField(max_length=20, blank=True, null=True)
    guarantor_phone_number = models.CharField(max_length=20, blank=True, null=True)
    guarantor_address = models.TextField(blank=True, null=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ["last_name", "first_name"]


class SalaryWorkers(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    contract = models.ForeignKey(Contract, on_delete=models.PROTECT)
    address = models.TextField(blank=True, null=True)
    craft_specialty = models.CharField(max_length=100, blank=True, null=True)
    years_of_experience = models.PositiveIntegerField(blank=True, null=True)
    image = models.ImageField(blank=True, null=True)
    date_joined = models.DateField(auto_now_add=True)
    date_left = models.DateField(auto_now_add=True)
    guarantor_name = models.CharField(max_length=20, blank=True, null=True)
    guarantor_phone_number = models.CharField(max_length=20, blank=True, null=True)
    guarantor_address = models.TextField(blank=True, null=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    pay = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ["last_name", "first_name"]


# class Pay(models.Model):
#     artisan = models.ForeignKey(Artisans, on_delete=models.CASCADE)
#     product = models.ForeignKey(Product, on_delete=models.PROTECT)
#     amount = models.IntegerField()
#
#     def __str__(self):
#         return f"{self.artisan.first_name} {self.artisan.last_name} pay"