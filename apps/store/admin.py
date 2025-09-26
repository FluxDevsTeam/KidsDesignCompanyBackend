from django.contrib import admin
from .models import RawMaterial, Removed, StoreCategory, AddRawMaterials

# Register your models here.
admin.site.register(RawMaterial)
admin.site.register(StoreCategory)
admin.site.register(AddRawMaterials)
admin.site.register(Removed)

