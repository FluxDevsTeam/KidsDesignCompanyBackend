from django.contrib import admin
from .models import Product, Quotation, ProductContractor, ProductSalaryWorker
# Register your models here.

admin.site.register(Product)
admin.site.register(Quotation)
admin.site.register(ProductContractor)
admin.site.register(ProductSalaryWorker)

