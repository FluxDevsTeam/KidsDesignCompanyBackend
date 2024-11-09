from django.db import models


class Customer(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ["last_name", "first_name"]


# class Payment(models.Model):
#     customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
#     amount = models.IntegerField()
#
#     def __str__(self):
#         return f"{self.customer.first_name} {self.customer.last_name} payment"
