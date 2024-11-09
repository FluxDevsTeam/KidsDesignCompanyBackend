from django.contrib import admin
from .models import Product, Quotation, RawMaterialUsed
# Register your models here.

admin.site.register(Product)
admin.site.register(Quotation)
admin.site.register(RawMaterialUsed)

