from django.db import models


class InventoryItem(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="shop/", blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)  # Quantity in stock
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    dimensions = models.CharField(max_length=100)

    @property
    def total_price(self):
        return self.stock * self.selling_price

    @property
    def profit(self):
        return self.selling_price - self.cost_price

    def __str__(self):
        return self.name


class Sold(models.Model):
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    date = models.DateField(auto_now_add=True)

    @property
    def total_price(self):
        return self.quantity * self.item.selling_price

    @property
    def profit(self):
        return (self.item.selling_price - self.item.cost_price) * self.quantity

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-date"]
