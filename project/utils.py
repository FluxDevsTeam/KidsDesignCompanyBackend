from .models import OverheadCost


def get_overhead_cost_instance():
    instance, created = OverheadCost.objects.get_or_create(id=1)
    return instance.overhead_cost_base
