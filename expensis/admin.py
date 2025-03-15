from django.contrib import admin
from .models import Assets, ExpenseCategory, Expense

# Register the models
admin.site.register(Assets)
admin.site.register(ExpenseCategory)
admin.site.register(Expense)
