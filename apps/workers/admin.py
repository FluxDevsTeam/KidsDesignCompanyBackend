from django.contrib import admin
from .models import Contractors, SalaryWorkers, Paid, SalaryWorkersRecord, ContractorRecord

# Register your models here.
admin.site.register(Contractors)
admin.site.register(SalaryWorkers)
admin.site.register(Paid)
admin.site.register(SalaryWorkersRecord)
admin.site.register(ContractorRecord)
