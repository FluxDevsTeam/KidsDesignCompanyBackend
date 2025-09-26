from django.contrib import admin
from .models import Project, OtherProduction, OverheadCost

# Register your models here.
admin.site.register(Project)
admin.site.register(OtherProduction)
admin.site.register(OverheadCost)