from django.contrib import admin
from .models import Income, IncomeCategory, Balance, BalanceSwitchLog

# Register the models
admin.site.register(Income)
admin.site.register(IncomeCategory)
admin.site.register(Balance)
admin.site.register(BalanceSwitchLog)
