from django.contrib import admin
from .models import InventoryItem, Sold, AddStock, InventoryCategory
# Register your models here.

admin.site.register(InventoryItem)
admin.site.register(Sold)
admin.site.register(AddStock)
admin.site.register(InventoryCategory)