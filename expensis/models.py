from django.db import models


class Expense(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.description})"

    class Meta:
        ordering = ["-date"]
