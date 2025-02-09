from django.contrib import admin
from .models import Expense, Assets, ExpenseCategory
# Register your models here.
admin.site.register(Expense)
admin.site.register(Assets)
admin.site.register(ExpenseCategory)
