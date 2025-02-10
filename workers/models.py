from django.db import models
from django.core.exceptions import ValidationError


class Contractors(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    craft_specialty = models.CharField(max_length=100, blank=True, null=True)
    years_of_experience = models.PositiveIntegerField(blank=True, null=True)
    image = models.ImageField(blank=True, null=True)
    agreement_form_image = models.ImageField(blank=True, null=True)
    date_joined = models.DateField(auto_now_add=True)
    date_left = models.DateField(auto_now_add=True)
    guarantor_name = models.CharField(max_length=20, blank=True, null=True)
    guarantor_phone_number = models.CharField(max_length=20, blank=True, null=True)
    guarantor_address = models.TextField(blank=True, null=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    is_still_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ["last_name", "first_name"]


class SalaryWorkers(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    craft_specialty = models.CharField(max_length=100, blank=True, null=True)
    years_of_experience = models.PositiveIntegerField(blank=True, null=True)
    image = models.ImageField(blank=True, null=True)
    agreement_form_image = models.ImageField(blank=True, null=True)
    date_joined = models.DateField(auto_now_add=True)
    date_left = models.DateField(auto_now_add=True)
    guarantor_name = models.CharField(max_length=20, blank=True, null=True)
    guarantor_phone_number = models.CharField(max_length=20, blank=True, null=True)
    guarantor_address = models.TextField(blank=True, null=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    is_still_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ["last_name", "first_name"]


class ContractorRecord(models.Model):
    report = models.TextField()
    date = models.DateField(auto_now=True)
    contractor = models.ForeignKey(Contractors, on_delete=models.CASCADE)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"contractor record on {self.date} - {self.report[:20]}"


class SalaryWorkersRecord(models.Model):
    report = models.TextField()
    date = models.DateField(auto_now=True)
    salary_worker = models.ForeignKey(SalaryWorkers, on_delete=models.CASCADE)

    def __str__(self):
        return f"salary_worker record on {self.date} - {self.report[:20]}"

    class Meta:
        ordering = ["-date"]