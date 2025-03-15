from django.contrib import admin
from .models import Contractors, SalaryWorkers, Paid

# Register your models here.
admin.site.register(Contractors)
admin.site.register(SalaryWorkers)
admin.site.register(Paid)
