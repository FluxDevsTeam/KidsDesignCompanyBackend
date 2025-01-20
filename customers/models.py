from django.db import models


class Customer(models.Model):
    name = models.CharField(unique=True,max_length=100)
    email = models.EmailField(unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ["name"]


# class Payment(models.Model):
#     customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
#     amount = models.IntegerField()
#
#     def __str__(self):
#         return f"{self.customer.first_name} {self.customer.last_name} payment"
