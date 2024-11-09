from django.contrib import admin
from .models import InventoryItem, Sold
# Register your models here.

admin.site.register(InventoryItem)
admin.site.register(Sold)

