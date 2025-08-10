from decimal import Decimal
from django.db import models
from datetime import date
from django.core.exceptions import ValidationError


class Balance(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    cash = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0"))
    bank = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0"))
    debt = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0"))

    def __str__(self):
        return f"balance: {self.id}"


class IncomeCategory(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.name}"


class Income(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(IncomeCategory, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    cash = models.BooleanField(default=False)
    date = models.DateField(default=date.today)

    def __str__(self):
        return f"{self.name}"

class PaymentSwitchLog(models.Model):
    expense = models.ForeignKey('Expense', on_delete=models.CASCADE, related_name='payment_switches')
    expense_payment = models.ForeignKey('ExpensePayment', on_delete=models.CASCADE)
    old_payment_method = models.CharField(max_length=20, choices=ExpensePayment.PAYMENT_METHODS)
    new_payment_method = models.CharField(max_length=20, choices=ExpensePayment.PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    switch_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Switch for {self.expense.name}: {self.old_payment_method} to {self.new_payment_method} ({self.amount}) on {self.switch_date}"

    def clean(self):
        if self.old_payment_method == self.new_payment_method:
            raise ValidationError("Old and new payment methods must be different")
        if self.amount <= 0:
            raise ValidationError("Switch amount must be positive")