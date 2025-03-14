from django.db import models

from rest_framework import viewsets
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Sum, Q, F, Count, Subquery, OuterRef, FloatField, ExpressionWrapper
from django.db.models.functions import Coalesce
from dateutil.relativedelta import relativedelta
from customers.models import Customer
from expensis.models import Assets, ExpenseCategory, Expense
from products.models import ProductContractor
from store.models import RawMaterial, Removed, AddRawMaterials
from shop.models import InventoryItem, Sold, AddStock
from datetime import timedelta
from workers.models import Contractors, SalaryWorkers, Paid
from project.models import Project, OtherProduction
from .seralizers import SimpleCustomerSerializer


class ApiStorekeeper(viewsets.ViewSet):

    def list(self, request):
        today = timezone.now().date()
        start_month = today.replace(day=1)
        one_year_ago = today - timezone.timedelta(days=365)

        # modoels
        raw_materials = RawMaterial.objects.all()
        removed = Removed.objects.all()
        add_raw_material = AddRawMaterials.objects.all()

        total_raw_materials = raw_materials.aggregate(total=Sum('quantity'))['total'] or 0
        total_value = raw_materials.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
        removed_cost_month = removed.filter(date__month=today.month).aggregate(total=Sum('price'))['total'] or 0
        removed_amount_year = removed.filter(date__year=today.year).aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
        added_amount_year = add_raw_material.filter(date__year=today.year).aggregate(total=Sum(F('item__price') * F('quantity')))['total'] or 0
        added_amount_this_month = add_raw_material.filter(date__month=today.month).aggregate(total=Sum(F('item__price') * F('quantity')))['total'] or 0

        monthly_added = []
        monthly_removed = []

        for i in range(12):
            month_start = today.replace(day=1) - timezone.timedelta(days=30 * i)
            month_end = (month_start + timezone.timedelta(days=32)).replace(day=1) - timezone.timedelta(days=1)

            added_total = add_raw_material.filter(
                date__date__gte=month_start,
                date__date__lte=month_end
            ).aggregate(total=Sum(F('item__price') * F('quantity')))['total'] or 0

            removed_total = removed.filter(
                date__gte=month_start,
                date__lte=month_end
            ).aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0

            monthly_added.append({
                'month': month_start.strftime("%b %Y"),
                'total': float(added_total)
            })

            monthly_removed.append({
                'month': month_start.strftime("%b %Y"),
                'total': float(removed_total)
            })

        monthly_added.reverse()
        monthly_removed.reverse()
        category_data = []
        categories = set(raw_materials.values_list('category__name', flat=True))
        for category_name in categories:
            if category_name:
                category_items = raw_materials.filter(category__name=category_name)
                category_materials_value = category_items.aggregate(
                    stock_value=Coalesce(Sum(F('quantity') * F('price')), 0.0, output_field=models.DecimalField(max_digits=10, decimal_places=2))) ['stock_value'] or 0.0

                category_data.append({
                    "category": category_name,
                    "materials_count": category_items.count(),
                    "total_materials_value": float(category_materials_value),
                })

        data = {
            'total_raw_materials': total_raw_materials,
            'total_value': total_value,
            'removed_cost_month': removed_cost_month,
            'removed_amount_year': removed_amount_year,
            'added_amount_this_year': added_amount_year,
            'added_amount_this_month': added_amount_this_month,
            "shop_category_data": category_data,
            'added_amount_monthly': monthly_added,
            'removed_amount_monthly': monthly_removed,
        }

        return Response(data)


class ApiShopkeeper(viewsets.ViewSet):
    def list(self, request):
        today = timezone.now().date()
        one_year_ago = today - timezone.timedelta(days=365)
        current_month_start = today.replace(day=1)
        next_month = today.replace(day=28) + timezone.timedelta(days=4)
        current_month_end = next_month - timezone.timedelta(days=next_month.day)

        inventory = InventoryItem.objects.all()
        sold = Sold.objects.all()
        add_stock = AddStock.objects.all()

        total_shop_value = inventory.aggregate(
            total=Sum(F('stock') * F('selling_price'))
        )['total'] or 0

        total_cost_value = inventory.aggregate(
            total=Sum(F('stock') * F('cost_price'))
        )['total'] or 0

        total_profit_potential = inventory.aggregate(
            total=Sum((F('selling_price') - F('cost_price')) * F('stock'))
        )['total'] or 0

        # Yearly aggregates
        yearly_profit = sold.filter(date__gte=one_year_ago).aggregate(
            total=Sum((F('selling_price') - F('cost_price')) * F('quantity'))
        )['total'] or 0

        yearly_added_value = add_stock.filter(date__gte=one_year_ago).aggregate(
            total=Sum(F('item__cost_price') * F('quantity'))
        )['total'] or 0

        # Current month aggregates
        total_sold_this_month = sold.filter(
            date__gte=current_month_start,
            date__lte=current_month_end
        ).aggregate(
            total=Sum(F('selling_price') * F('quantity'))
        )['total'] or 0

        total_added_this_month = add_stock.filter(
            date__gte=current_month_start,
            date__lte=current_month_end
        ).aggregate(
            total=Sum(F('item__cost_price') * F('quantity'))
        )['total'] or 0

        total_profit_this_month = sold.filter(
            date__gte=current_month_start,
            date__lte=current_month_end
        ).aggregate(
            total=Sum((F('selling_price') - F('cost_price')) * F('quantity'))
        )['total'] or 0

        # Monthly breakdowns
        monthly_profit = []
        monthly_added_value = []
        amount_sold_monthly = []

        for i in range(12):
            month_start = (today.replace(day=1) - relativedelta(months=i))
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)

            # Monthly profit
            month_profit = sold.filter(
                date__gte=month_start,
                date__lte=month_end
            ).aggregate(
                total=Sum((F('selling_price') - F('cost_price')) * F('quantity'))
            )['total'] or 0

            # Monthly added stock value
            month_added = add_stock.filter(
                date__gte=month_start,
                date__lte=month_end
            ).aggregate(
                total=Sum(F('item__cost_price') * F('quantity'))
            )['total'] or 0

            # Monthly sales value
            month_sold = sold.filter(
                date__gte=month_start,
                date__lte=month_end
            ).aggregate(
                total=Sum(F('selling_price') * F('quantity'))
            )['total'] or 0

            monthly_profit.append({
                'month': month_start.strftime("%b %Y"),
                'total': float(month_profit)
            })

            monthly_added_value.append({
                'month': month_start.strftime("%b %Y"),
                'total': float(month_added)
            })

            amount_sold_monthly.append({
                'month': month_start.strftime("%b %Y"),
                'total': float(month_sold)
            })

        # Reverse for chronological order
        monthly_profit.reverse()
        monthly_added_value.reverse()
        amount_sold_monthly.reverse()
        category_data = []
        categories = set(inventory.values_list('category__name', flat=True))
        for category_name in categories:
            if category_name:
                category_items = inventory.filter(category__name=category_name)
                category_stock_value = category_items.aggregate(
                    stock_value=Coalesce(Sum(F('stock') * F('selling_price')), 0.0, output_field=models.DecimalField(max_digits=10, decimal_places=2))) ['stock_value'] or 0.0
                category_cost_value = category_items.aggregate(
                    cost_value=Coalesce(Sum(F('stock') * F('cost_price')), 0.0, output_field=models.DecimalField(max_digits=10, decimal_places=2))
                )['cost_value'] or 0.0

                category_profit = category_stock_value - category_cost_value

                category_data.append({
                    "category": category_name,
                    "total_stock_value": float(category_stock_value),
                    "total_cost_value": float(category_cost_value),
                    "total_profit": float(category_profit),
                })
        data = {
            'total_shop_value': total_shop_value,
            'total_cost_value': total_cost_value,
            'total_profit_potential': total_profit_potential,
            "shop_category_data": category_data,
            'yearly_profit': yearly_profit,
            'yearly_added_value': yearly_added_value,
            'total_sold_this_month': total_sold_this_month,
            'total_added_this_month': total_added_this_month,
            'total_profit_this_month': total_profit_this_month,
            'monthly_profit': monthly_profit,
            'monthly_added_value': monthly_added_value,
            'amount_sold_monthly': amount_sold_monthly
        }

        return Response(data)


class ApiAdminDashboard(viewsets.ViewSet):
    def list(self, request):
        today = timezone.now().date()
        assets = Assets.objects.all()
        expense = Expense.objects.all()
        paid = Paid.objects.all()
        all_salary_workers = SalaryWorkers.objects.all()
        all_contractors = Contractors.objects.all()
        # Financial Health
        total_expenses = expense.aggregate(total=Sum('amount'))['total'] or 0
        active_assets = assets.filter(is_still_available=True).aggregate(total=Sum('value'))['total'] or 0
        deprecated_assets = assets.filter(is_still_available=False).aggregate(total=Sum('value'))['total'] or 0

        categories = ExpenseCategory.objects.annotate(total=Sum('expense__amount')).filter(total__gt=0).order_by(
            '-total')

        expensis_category_breakdown = []
        for cat in categories:
            percentage = ((cat.total / total_expenses) * 100) if total_expenses else 0
            expensis_category_breakdown.append({
                'category': cat.name,
                'total': cat.total,
                'percentage': round(percentage, 2)
            })

        # Monthly Trend with Others
        monthly_trend = []
        for i in range(12):
            month_start = (today.replace(day=1) - relativedelta(months=i))
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)

            month_total = expense.filter(
                date__gte=month_start,
                date__lte=month_end
            ).aggregate(total=Sum('amount'))['total'] or 0

            project_total = expense.filter(
                project__isnull=False,
                date__range=[month_start, month_end]
            ).aggregate(total=Sum('amount'))['total'] or 0

            shop_total = expense.filter(
                shop__isnull=False,
                date__range=[month_start, month_end]
            ).aggregate(total=Sum('amount'))['total'] or 0

            others_total = month_total - (project_total + shop_total)

            monthly_trend.append({
                'month': month_start.strftime("%b %Y"),
                'total': float(month_total),
                'type_breakdown': {
                    'project': float(project_total),
                    'shop': float(shop_total),
                    'others': float(others_total)
                }
            })
        start_of_week = today - timezone.timedelta(days=today.weekday())
        # Top 5 Categories
        top_categories = ExpenseCategory.objects.annotate(total=Sum('expense__amount')).filter(total__gt=0).order_by(
            '-total')[:5].values('name', 'total')
        monthly_total_paid = paid.filter(date__month=today.month).aggregate(Sum('amount'))['amount__sum'] or 0.0
        weekly_total_paid = paid.filter(date__range=[start_of_week, today]).aggregate(Sum('amount'))[
                                'amount__sum'] or 0.0

        salary_workers_count = all_salary_workers.count()
        active_salary_workers_count = all_salary_workers.filter(is_still_active=True).count()
        total_salary_workers_monthly_pay = all_salary_workers.aggregate(total=Sum("salary"))["total"] or 0.0
        total_paid = all_salary_workers.filter(paid__date__month=today.month).aggregate(total=Sum("paid__amount"))[
                         "total"] or 0.0

        all_contractors_count = all_contractors.count()
        all_active_contractors_count = all_contractors.filter(is_still_active=True).count()

        total_contractors_monthly_pay = \
        all_contractors.filter(paid__date__month=today.month).aggregate(total=Sum("paid__amount"))["total"] or 0.0

        total_contractors_weekly_pay = \
        all_contractors.filter(paid__date__range=(start_of_week, today)).aggregate(total=Sum("paid__amount"))[
            "total"] or 0.0

        data = {
            'financial_health': {
                'total_expenses': total_expenses,
                'active_assets': active_assets,
                'deprecated_assets': deprecated_assets
            },
            'workers': {
                "salary_workers_count": salary_workers_count,
                "active_salary_workers_count": active_salary_workers_count,
                "total_salary_workers_monthly_pay": total_salary_workers_monthly_pay,
                "all_contractors_count": all_contractors_count,
                "all_active_contractors_count": all_active_contractors_count,
            },
            'paid': {
                'monthly_total_paid': monthly_total_paid,
                'weekly_total_paid': weekly_total_paid,
                "total_paid": total_paid,
                "total_contractors_monthly_pay": total_contractors_monthly_pay,
                "total_contractors_weekly_pay": total_contractors_weekly_pay,
            },

            'expense_category_breakdown': expensis_category_breakdown,
            'monthly_expense_trend': list(reversed(monthly_trend)),
            'top_categories': top_categories,
        }

        return Response(data)


class ApiFactoryManagerDashboard(viewsets.ViewSet):

    def list(self, request):
        today = timezone.now().date()
        assets = Assets.objects.all()
        expense = Expense.objects.all()
        sold = Sold.objects.all()
        project = Project.objects.all()
        paid = Paid.objects.all()
        customer = Customer.objects.all()
        all_salary_workers = SalaryWorkers.objects.all()
        all_contractors = Contractors.objects.all()
        # customer
        owing_customers = SimpleCustomerSerializer(customer.filter(project__balance__gte=1).distinct(), many=True).data
        owing_customers_count = customer.filter(project__balance__gte=1).distinct().count()
        all_customers = customer.count()
        all_active_customers = customer.filter(project__is_delivered=False).distinct().count()

        # Financial Health
        sales_count_this_month = sold.filter(date__month=today.month).count()
        total_project_sales_this_month = \
        sold.filter(date__month=today.month, logistics=None).aggregate(total=Sum(F('selling_price') * F('quantity')))[
            'total'] or 0
        total_non_project_sales_this_month = \
        sold.filter(date__month=today.month, project=None).aggregate(total=Sum(F('selling_price') * F('quantity')))[
            'total'] or 0
        total_sold_this_month = \
        sold.filter(date__month=today.month).aggregate(total=Sum(F('selling_price') * F('quantity')))['total'] or 0
        total_sold_profit_this_month = sold.filter(date__month=today.month).aggregate(
            total=Sum((F('selling_price') * F('quantity')) - (F('cost_price') * F('quantity'))))['total'] or 0
        project_count_this_month = project.filter(start_date__month=today.month).count()
        total_project_amount_this_month = project.filter(start_date__month=today.month).aggregate(
            total=Sum(F('selling_price') + F('logistics') + F('service_charge')))['total'] or 0
        total_income_this_month = total_project_amount_this_month + \
                                  sold.filter(date__month=today.month, project=None).aggregate(
                                      total=Sum(F('selling_price') * F('quantity')))['total'] or 0
        total_expenses = expense.aggregate(total=Sum('amount'))['total'] or 0
        active_assets = assets.filter(is_still_available=True).aggregate(total=Sum('value'))['total'] or 0
        deprecated_assets = assets.filter(is_still_available=False).aggregate(total=Sum('value'))['total'] or 0

        categories = ExpenseCategory.objects.annotate(total=Sum('expense__amount')).filter(total__gt=0).order_by(
            '-total')

        expensis_category_breakdown = []
        for cat in categories:
            percentage = ((cat.total / total_expenses) * 100) if total_expenses else 0
            expensis_category_breakdown.append({
                'category': cat.name,
                'total': cat.total,
                'percentage': round(percentage, 2)
            })

        # Monthly Trend with Others
        monthly_trend = []
        for i in range(12):
            month_start = (today.replace(day=1) - relativedelta(months=i))
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)

            month_total = expense.filter(
                date__gte=month_start,
                date__lte=month_end
            ).aggregate(total=Sum('amount'))['total'] or 0

            project_total = expense.filter(
                project__isnull=False,
                date__range=[month_start, month_end]
            ).aggregate(total=Sum('amount'))['total'] or 0

            shop_total = expense.filter(
                shop__isnull=False,
                date__range=[month_start, month_end]
            ).aggregate(total=Sum('amount'))['total'] or 0

            others_total = month_total - (project_total + shop_total)

            monthly_trend.append({
                'month': month_start.strftime("%b %Y"),
                'total': float(month_total),
                'type_breakdown': {
                    'project': float(project_total),
                    'shop': float(shop_total),
                    'others': float(others_total)
                }
            })
        start_of_week = today - timezone.timedelta(days=today.weekday())
        # Top 5 Categories
        top_categories = ExpenseCategory.objects.annotate(total=Sum('expense__amount')).filter(total__gt=0).order_by(
            '-total')[:5].values('name', 'total')
        monthly_total_paid = paid.filter(date__month=today.month).aggregate(Sum('amount'))['amount__sum'] or 0.0
        weekly_total_paid = paid.filter(date__range=[start_of_week, today]).aggregate(Sum('amount'))[
                                'amount__sum'] or 0.0

        salary_workers_count = all_salary_workers.count()
        active_salary_workers_count = all_salary_workers.filter(is_still_active=True).count()
        total_salary_workers_monthly_pay = all_salary_workers.aggregate(total=Sum("salary"))["total"] or 0.0
        total_paid = all_salary_workers.filter(paid__date__month=today.month).aggregate(total=Sum("paid__amount"))[
                         "total"] or 0.0

        all_contractors_count = all_contractors.count()
        all_active_contractors_count = all_contractors.filter(is_still_active=True).count()

        total_contractors_monthly_pay = \
        all_contractors.filter(paid__date__month=today.month).aggregate(total=Sum("paid__amount"))["total"] or 0.0

        total_contractors_weekly_pay = \
        all_contractors.filter(paid__date__range=(start_of_week, today)).aggregate(total=Sum("paid__amount"))[
            "total"] or 0.0

        data = {
            'financial_health': {
                'sales_count_this_month': sales_count_this_month,
                'total_project_sales_this_month': total_project_sales_this_month,
                'total_non_project_sales_this_month': total_non_project_sales_this_month,
                'total_shop_items_sold_this_month': total_sold_this_month,
                'total_shop_profit_this_month': total_sold_profit_this_month,
                'project_count_this_month': project_count_this_month,
                'total_project_amount_this_month': total_project_amount_this_month,
                'total_income_this_month': total_income_this_month,
                'total_expenses': total_expenses,
                'active_assets': active_assets,
                'deprecated_assets': deprecated_assets
            },
            'customers': {
                "all_customers_count": all_customers,
                "active_customers_count": all_active_customers,
                'owing_customers_count': owing_customers_count,
                'owing_customers': owing_customers
            },

            'workers': {
                "salary_workers_count": salary_workers_count,
                "active_salary_workers_count": active_salary_workers_count,
                "total_salary_workers_monthly_pay": total_salary_workers_monthly_pay,
                "all_contractors_count": all_contractors_count,
                "all_active_contractors_count": all_active_contractors_count,
            },
            'paid': {
                'monthly_total_paid': monthly_total_paid,
                'weekly_total_paid': weekly_total_paid,
                "total_paid": total_paid,
                "total_contractors_monthly_pay": total_contractors_monthly_pay,
                "total_contractors_weekly_pay": total_contractors_weekly_pay,
            },

            'expense_category_breakdown': expensis_category_breakdown,
            'monthly_expense_trend': list(reversed(monthly_trend)),
            'top_categories': top_categories,
        }
        return Response(data)


class CEODashboardViewSet(viewsets.ViewSet):
    def list(self, request):
        today = timezone.now().date()
        start_of_year = today.replace(month=1, day=1)
        start_of_month = today.replace(day=1)

        # Helper function for monthly aggregates
        def get_monthly_data(model, date_field, value_field):
            monthly_data = []
            for i in range(12):
                month_start = (today.replace(day=1) - relativedelta(months=i))
                month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
                total = model.objects.filter(
                    **{f"{date_field}__gte": month_start, f"{date_field}__lte": month_end}
                ).aggregate(total=Sum(value_field))['total'] or 0
                monthly_data.append({
                    'month': month_start.strftime("%b %Y"),
                    'total': float(total)
                })
            return list(reversed(monthly_data))

        # Financial Metrics for the year
        total_shop_income_year = Sold.objects.filter(date__gte=start_of_year).aggregate(total=Sum(F('selling_price') * F('quantity')))['total'] or 0
        total_non_project_shop_income_year = Sold.objects.filter(project__isnull=True, date__gte=start_of_year).aggregate(total=Sum(F('selling_price') * F('quantity')))['total'] or 0

        total_projects_income_year = Project.objects.filter(start_date__gte=start_of_year).aggregate(total=Sum(F('selling_price') + F('logistics') + F('service_charge')))['total'] or 0
        no_shop_projects_income_year = Project.objects.filter(start_date__gte=start_of_year).aggregate(total=Sum(F('selling_price') + F('logistics') + F('service_charge') - (total_shop_income_year -total_non_project_shop_income_year)))['total'] or 0

        total_income_year = no_shop_projects_income_year + total_shop_income_year

        # Financial Metrics for the current month
        total_shop_income_month = Sold.objects.filter(project__isnull=True, date__gte=start_of_month).aggregate(total=Sum(F('selling_price') * F('quantity')))['total'] or 0
        total_non_project_shop_income_month = Sold.objects.filter(project__isnull=True, date__gte=start_of_month).aggregate(total=Sum(F('selling_price') * F('quantity')))['total'] or 0

        total_projects_income_month = Project.objects.filter(start_date__gte=start_of_month).aggregate(total=Sum(F('selling_price') + F('logistics') + F('service_charge')))['total'] or 0
        no_shop_projects_income_month = Project.objects.filter(start_date__gte=start_of_month).aggregate(total=Sum(F('selling_price') + F('logistics') + F('service_charge') - (total_shop_income_year -total_non_project_shop_income_year)))['total'] or 0

        total_income_month = no_shop_projects_income_month + total_shop_income_month

        # Expenses Breakdown for the year
        salary_costs_year = Paid.objects.filter(contract__isnull=True, date__gte=start_of_year).aggregate(total=Sum('amount'))['total'] or 0

        contractor_costs_year = ProductContractor.objects.filter(product__project__start_date__gte=start_of_year).aggregate(total=Sum('cost'))['total'] or 0

        raw_material_costs_year = AddRawMaterials.objects.filter(date__gte=start_of_year).aggregate(total=Sum(F('item__price') * F('quantity')))['total'] or 0

        asset_costs_year = Assets.objects.filter(date_added__gte=start_of_year).aggregate(total=Sum('value'))['total'] or 0

        other_expenses_year = Expense.objects.filter(date__gte=start_of_year).aggregate(total=Sum('amount'))['total'] or 0

        other_production_expensis_year = OtherProduction.objects.filter(project__start_date__gte=start_of_year).aggregate(total=Sum('cost'))['total'] or 0

        sold_cost_year = Sold.objects.filter(date__gte=start_of_year).aggregate(total=Sum(F('cost_price') * F('quantity')))['total'] or 0

        total_expenses_year = sum([sold_cost_year + salary_costs_year, contractor_costs_year, raw_material_costs_year, other_expenses_year + other_production_expensis_year])

        # Expenses Breakdown for the current month
        salary_costs_month = SalaryWorkers.objects.filter(is_still_active=True).aggregate(total=Sum('salary'))['total'] or 0

        contractor_costs_month = ProductContractor.objects.filter(product__project__start_date__year=start_of_month.year, product__project__start_date__month=start_of_month.month).aggregate(total=Sum('cost'))['total'] or 0

        raw_material_costs_month = AddRawMaterials.objects.filter(date__year=start_of_month.year, date__month=start_of_month.month).aggregate(total=Sum(F('item__price') * F('quantity')))['total'] or 0

        asset_costs_month = Assets.objects.filter(date_added__year=start_of_month.year, date_added__month=start_of_month.month).aggregate(total=Sum('value'))['total'] or 0

        other_expenses_month = Expense.objects.filter(date__year=start_of_month.year, date__month=start_of_month.month).aggregate(total=Sum('amount'))['total'] or 0

        other_production_expensis_month = OtherProduction.objects.filter(project__start_date__gte=start_of_month).aggregate(total=Sum('cost'))['total'] or 0

        sold_cost_month = Sold.objects.filter(date__gte=start_of_month).aggregate(total=Sum(F('cost_price') * F('quantity')))['total'] or 0

        total_expenses_month = sum([sold_cost_month + salary_costs_month, contractor_costs_month, raw_material_costs_month, other_expenses_month + other_production_expensis_month])

        # Profit Calculations for the year
        profit_year = total_income_year - total_expenses_year

        # Profit Calculations for the current month
        profit_month = total_income_month - total_expenses_month

        # Inventory Value
        inventory_value = InventoryItem.objects.aggregate(total=Sum(F('stock') * F('selling_price')))['total'] or 0

        # Store Value
        total_store_value = RawMaterial.objects.aggregate(total=Sum(F('quantity') * F('price')))['total'] or 0

        # Monthly Trends
        monthly_income = get_monthly_data(Sold, 'date', F('selling_price') * F('quantity'))

        monthly_expenses = []
        for i in range(12):
            month_start = today.replace(day=1) - relativedelta(months=i)
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)

            expenses = {
                'salary': SalaryWorkers.objects.filter(
                    is_still_active=True
                ).aggregate(total=Sum('salary'))['total'] or 0,
                'contractors': ProductContractor.objects.filter(
                    product__project__start_date__year=month_start.year,
                    product__project__start_date__month=month_start.month
                ).aggregate(total=Sum('cost'))['total'] or 0,
                'materials': AddRawMaterials.objects.filter(
                    date__year=month_start.year,
                    date__month=month_start.month
                ).aggregate(total=Sum(F('item__price') * F('quantity')))['total'] or 0,
                'other_expensis': Expense.objects.filter(
                    date__year=month_start.year,
                    date__month=month_start.month
                ).aggregate(total=Sum('amount'))['total'] or 0,
                'other_production_expensis': OtherProduction.objects.filter(
                    project__start_date__year=month_start.year,
                    project__start_date__month=month_start.month
                ).aggregate(total=Sum('cost'))['total'] or 0,
                'sold_cost': Sold.objects.filter(
                    date__year=month_start.year,
                    date__month=month_start.month
                ).aggregate(total=Sum('cost_price'))['total'] or 0
            }

            monthly_expenses.append({
                'month': month_start.strftime("%b %Y"),
                'total': sum(expenses.values()),
                'breakdown': expenses
            })

        monthly_expenses.reverse()

        # Categorical Breakdowns for the year
        expense_categories_year = ExpenseCategory.objects.filter(expense__date__gte=start_of_year).annotate(total=Sum('expense__amount')).values('name', 'total').order_by('-total')

        # Categorical Breakdowns for the month
        expense_categories_month = ExpenseCategory.objects.annotate(total=Sum('expense__amount', filter=Q(expense__date__gte=start_of_month))).values('name', 'total').order_by('-total')

        # Asset Analysis
        asset_analysis = Assets.objects.aggregate(active=Sum('value', filter=Q(is_still_available=True)), deprecated=Sum('value', filter=Q(is_still_available=False)))

        # Customer Analysis
        total_customers = Customer.objects.count()
        active_customers = Customer.objects.filter(project__is_delivered=False).distinct().count()
        owing_customers = Customer.objects.filter(project__balance__gte=1).distinct().count()

        # Worker Analysis
        total_salary_workers = SalaryWorkers.objects.count()
        active_salary_workers = SalaryWorkers.objects.filter(is_still_active=True).count()
        total_contractors = Contractors.objects.count()
        active_contractors = Contractors.objects.filter(is_still_active=True).count()

        data = {
            'key_metrics': {
                'total_income_year': round(total_income_year, 2),
                'total_expenses_year': round(total_expenses_year, 2),
                'total_profit_year': round(profit_year, 2),
                'total_income_month': round(total_income_month, 2),
                'total_expenses_month': round(total_expenses_month, 2),
                'profit_month': round(profit_month, 2),
                'current_assets_value': round(asset_analysis.get('active', 0), 2),
                'inventory_value': round(inventory_value, 2),
                'total_store_value': round(total_store_value, 2)
            },
            'income_breakdown_year': {
                'projects': round(total_projects_income_year, 2),
                'no_shop_projects': round(no_shop_projects_income_year, 2),
                'shop_sales': round(total_shop_income_year, 2),
                'non_project_shop_sales': round(total_non_project_shop_income_year, 2),
                'percentage_projects': round((no_shop_projects_income_year / total_income_year * 100) if total_income_year else 0, 2),
                'percentage_shop': round((total_shop_income_year / total_income_year * 100) if total_income_year else 0, 2)
            },
            'income_breakdown_month': {
                'projects': round(total_projects_income_month, 2),
                'no_shop_projects': round(no_shop_projects_income_month, 2),
                'shop_sales': round(total_shop_income_month, 2),
                'non_project_shop_sales': round(total_non_project_shop_income_month, 2),
                'percentage_projects': round((no_shop_projects_income_month / total_income_month * 100) if total_income_month else 0, 2),
                'percentage_shop': round((total_shop_income_month / total_income_month * 100) if total_income_month else 0, 2)
            },
            'expense_breakdown_year': {
                'salaries': round(salary_costs_year, 2),
                'contractors': round(contractor_costs_year, 2),
                'raw_materials': round(raw_material_costs_year, 2),
                'assets': round(asset_costs_year, 2),
                'factory_expenses': round(other_expenses_year, 2),
                'other_production_expensis': round(other_production_expensis_year, 2),
                'monthly_sold_cost_price': round(sold_cost_year, 2),
            },
            'expense_breakdown_month': {
                'salaries': round(salary_costs_month, 2),
                'contractors': round(contractor_costs_month, 2),
                'raw_materials': round(raw_material_costs_month, 2),
                'assets': round(asset_costs_month, 2),
                'factory_expenses': round(other_expenses_month, 2),
                'other_production_expensis': round(other_production_expensis_month, 2),
                'monthly_sold_cost_price': round(sold_cost_month, 2),
            },
            'monthly_trends': {
                'income': monthly_income,
                'expenses': monthly_expenses,
                'profit': [{
                    'month': m['month'],
                    'total': float(m['total'] or 0) - float(e['total'] or 0)
                } for m, e in zip(monthly_income, monthly_expenses)]
            },
            'categorical_data_year': {
                'expense_categories': [
                    {'name': cat['name'], 'value': cat['total']}
                    for cat in expense_categories_year if cat['total']
                ]
            },
            'categorical_data_month': {
                'expense_categories': [
                    {'name': cat['name'], 'value': cat['total']}
                    for cat in expense_categories_month if cat['total']
                ]
            },
            'asset_analysis': {
                'active_assets': asset_analysis.get('active', 0),
                'deprecated_assets': asset_analysis.get('deprecated', 0)
            },
            'additional_metrics': {
                'total_customers': total_customers,
                'active_customers': active_customers,
                'owing_customers': owing_customers,
                'total_salary_workers': total_salary_workers,
                'active_salary_workers': active_salary_workers,
                'total_contractors': total_contractors,
                'active_contractors': active_contractors,
                'inventory_items': InventoryItem.objects.count(),
                'raw_materials_types': RawMaterial.objects.count()
            }
        }

        return Response(data)

class ProjectManagerDashboardViewSet(viewsets.ViewSet):
    def list(self, request):
        today = timezone.now().date()
        start_of_year = today.replace(month=1, day=1)
        start_of_month = today.replace(day=1)

        # Helper function for monthly aggregates
        def get_monthly_data(model, date_field, value_field):
            monthly_data = []
            for i in range(12):
                month_start = today.replace(day=1) - relativedelta(months=i)
                month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
                total = model.objects.filter(
                    **{f"{date_field}__gte": month_start, f"{date_field}__lte": month_end}
                ).aggregate(total=Sum(value_field))['total'] or 0
                monthly_data.append({
                    'month': month_start.strftime("%b %Y"),
                    'total': float(total)
                })
            return list(reversed(monthly_data))

        # Project Statistics for the year
        total_projects_income_year = Project.objects.filter(
            start_date__gte=start_of_year
        ).aggregate(
            total=Sum(F('selling_price') + F('logistics') + F('service_charge'))
        )['total'] or 0

        total_shop_income_year = Sold.objects.filter(
            project__isnull=True, date__gte=start_of_year
        ).aggregate(
            total=Sum(F('selling_price') * F('quantity'))
        )['total'] or 0

        total_income_year = total_projects_income_year + total_shop_income_year

        # Project Statistics for the current month
        total_projects_income_month = Project.objects.filter(
            start_date__gte=start_of_month
        ).aggregate(
            total=Sum(F('selling_price') + F('logistics') + F('service_charge'))
        )['total'] or 0

        total_shop_income_month = Sold.objects.filter(
            project__isnull=True, date__gte=start_of_month
        ).aggregate(
            total=Sum(F('selling_price') * F('quantity'))
        )['total'] or 0

        total_income_month = total_projects_income_month + total_shop_income_month

        # Expenses Breakdown for the year
        salary_costs_year = SalaryWorkers.objects.filter(
            is_still_active=True
        ).aggregate(total=Sum('salary'))['total'] or 0

        contractor_costs_year = ProductContractor.objects.filter(
            product__project__start_date__gte=start_of_year
        ).aggregate(total=Sum('cost'))['total'] or 0

        raw_material_costs_year = AddRawMaterials.objects.filter(
            date__gte=start_of_year
        ).aggregate(
            total=Sum(F('item__price') * F('quantity'))
        )['total'] or 0

        asset_costs_year = Assets.objects.filter(
            date_added__gte=start_of_year
        ).aggregate(total=Sum('value'))['total'] or 0

        other_expenses_year = Expense.objects.filter(
            date__gte=start_of_year
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_expenses_year = sum([salary_costs_year, contractor_costs_year, raw_material_costs_year, asset_costs_year, other_expenses_year])

        # Expenses Breakdown for the current month
        salary_costs_month = SalaryWorkers.objects.filter(
            is_still_active=True
        ).aggregate(total=Sum('salary'))['total'] or 0

        contractor_costs_month = ProductContractor.objects.filter(
            product__project__start_date__year=start_of_month.year,
            product__project__start_date__month=start_of_month.month
        ).aggregate(total=Sum('cost'))['total'] or 0

        raw_material_costs_month = AddRawMaterials.objects.filter(
            date__year=start_of_month.year,
            date__month=start_of_month.month
        ).aggregate(
            total=Sum(F('item__price') * F('quantity'))
        )['total'] or 0

        asset_costs_month = Assets.objects.filter(
            date_added__year=start_of_month.year,
            date_added__month=start_of_month.month
        ).aggregate(total=Sum('value'))['total'] or 0

        other_expenses_month = Expense.objects.filter(
            date__year=start_of_month.year,
            date__month=start_of_month.month
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_expenses_month = sum([salary_costs_month, contractor_costs_month, raw_material_costs_month, asset_costs_month, other_expenses_month])

        # Profit Calculations for the year
        net_profit_year = total_income_year - total_expenses_year
        gross_profit_year = (total_projects_income_year + total_shop_income_year) - (
                raw_material_costs_year + salary_costs_year + contractor_costs_year)

        # Profit Calculations for the current month
        net_profit_month = total_income_month - total_expenses_month
        gross_profit_month = (total_projects_income_month + total_shop_income_month) - (
                raw_material_costs_month + salary_costs_month + contractor_costs_month)

        # Inventory Value
        inventory_value = InventoryItem.objects.aggregate(
            total=Sum(F('stock') * F('selling_price'))
        )['total'] or 0

        # Project Statistics with proper cost calculations
        project_profitability = Project.objects.annotate(
            # Calculate material costs
            material_cost=Coalesce(Subquery(
                Removed.objects.filter(product__project=OuterRef('pk'))
                .annotate(
                    cost=ExpressionWrapper(
                        F('quantity') * F('material__price'),
                        output_field=FloatField()
                    )
                )
                .values('product__project')
                .annotate(total=Sum('cost'))
                .values('total'),
                output_field=FloatField()
            ), 0.0),

            # Calculate artisan costs
            artisan_cost=Coalesce(Subquery(
                ProductContractor.objects.filter(product__project=OuterRef('pk'))
                .values('product__project')
                .annotate(total=Sum('cost'))
                .values('total'),
                output_field=FloatField()
            ), 0.0),

            # Calculate total product costs
            product_costs=ExpressionWrapper(
                F('material_cost') + F('artisan_cost'),
                output_field=FloatField()
            ),

            # Calculate total expenses
            expense_costs=Coalesce(Subquery(
                Expense.objects.filter(project=OuterRef('pk'))
                .values('project')
                .annotate(total=Sum('amount'))
                .values('total'),
                output_field=FloatField()
            ), 0.0),

            # Calculate other production costs
            production_costs=Coalesce(Subquery(
                OtherProduction.objects.filter(project=OuterRef('pk'))
                .values('project')
                .annotate(total=Sum('cost'))
                .values('total'),
                output_field=FloatField()
            ), 0.0),

            # Sum all costs
            total_project_cost=ExpressionWrapper(
                F('product_costs') + F('expense_costs') + F('production_costs'),
                output_field=FloatField()
            ),

            # Calculate profit
            profit=ExpressionWrapper(
                F('selling_price') - F('total_project_cost'),
                output_field=FloatField()
            )
        ).values('name', 'selling_price', 'total_project_cost', 'profit')

        project_stats = Project.objects.aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
            in_progress=Count('id', filter=Q(status='in_progress')),
            overdue=Count('id', filter=Q(status='overdue'))
        )

        # Monthly Trends
        monthly_income = get_monthly_data(
            Sold, 'date', F('selling_price') * F('quantity')
        )

        monthly_expenses = []
        for i in range(12):
            month_start = today.replace(day=1) - relativedelta(months=i)
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)

            expenses = {
                'salary': SalaryWorkers.objects.filter(
                    is_still_active=True
                ).aggregate(total=Sum('salary'))['total'] or 0,
                'contractors': ProductContractor.objects.filter(
                    product__project__start_date__year=month_start.year,
                    product__project__start_date__month=month_start.month
                ).aggregate(total=Sum('cost'))['total'] or 0,
                'materials': AddRawMaterials.objects.filter(
                    date__year=month_start.year,
                    date__month=month_start.month
                ).aggregate(total=Sum(F('item__price') * F('quantity')))['total'] or 0,
                'other': Expense.objects.filter(
                    date__year=month_start.year,
                    date__month=month_start.month
                ).aggregate(total=Sum('amount'))['total'] or 0
            }

            monthly_expenses.append({
                'month': month_start.strftime("%b %Y"),
                'total': sum(expenses.values()),
                'breakdown': expenses
            })

        monthly_expenses.reverse()

        # Categorical Breakdowns for the year
        expense_categories_year = ExpenseCategory.objects.annotate(
            total=Sum('expense__amount')
        ).values('name', 'total').order_by('-total')

        # Categorical Breakdowns for the month
        expense_categories_month = ExpenseCategory.objects.annotate(
            total=Sum('expense__amount', filter=Q(expense__date__gte=start_of_month))
        ).values('name', 'total').order_by('-total')

        # Asset Analysis
        asset_analysis = Assets.objects.aggregate(
            active=Sum('value', filter=Q(is_still_available=True)),
            deprecated=Sum('value', filter=Q(is_still_available=False))
        )

        data = {
            'key_metrics': {
                'total_income_year': round(total_income_year, 2),
                'total_expenses_year': round(total_expenses_year, 2),
                'net_profit_year': round(net_profit_year, 2),
                'gross_profit_year': round(gross_profit_year, 2),
                'total_income_month': round(total_income_month, 2),
                'total_expenses_month': round(total_expenses_month, 2),
                'net_profit_month': round(net_profit_month, 2),
                'gross_profit_month': round(gross_profit_month, 2),
                'current_assets_value': round(asset_analysis.get('active', 0), 2),
                'inventory_value': round(inventory_value, 2)
            },
            'income_breakdown_year': {
                'projects': round(total_projects_income_year, 2),
                'shop_sales': round(total_shop_income_year, 2),
                'percentage_projects': round((total_projects_income_year / total_income_year * 100) if total_income_year else 0, 2),
                'percentage_shop': round((total_shop_income_year / total_income_year * 100) if total_income_year else 0, 2)
            },
            'income_breakdown_month': {
                'projects': round(total_projects_income_month, 2),
                'shop_sales': round(total_shop_income_month, 2),
                'percentage_projects': round((total_projects_income_month / total_income_month * 100) if total_income_month else 0, 2),
                'percentage_shop': round((total_shop_income_month / total_income_month * 100) if total_income_month else 0, 2)
            },
            'expense_breakdown_year': {
                'salaries': round(salary_costs_year, 2),
                'contractors': round(contractor_costs_year, 2),
                'raw_materials': round(raw_material_costs_year, 2),
                'assets': round(asset_costs_year, 2),
                'other_expenses': round(other_expenses_year, 2),
                'operational_ratio': round((total_expenses_year / total_income_year * 100) if total_income_year else 0, 2)
            },
            'expense_breakdown_month': {
                'salaries': round(salary_costs_month, 2),
                'contractors': round(contractor_costs_month, 2),
                'raw_materials': round(raw_material_costs_month, 2),
                'assets': round(asset_costs_month, 2),
                'other_expenses': round(other_expenses_month, 2),
                'operational_ratio': round((total_expenses_month / total_income_month * 100) if total_income_month else 0, 2)
            },
            'project_statistics': {
                'total_projects': project_stats['total'],
                'completed': project_stats['completed'],
                'in_progress': project_stats['in_progress'],
                'overdue': project_stats['overdue'],
                'average_project_profit': round(
                    sum(p['profit'] for p in project_profitability) / project_stats['total']
                    if project_stats['total'] else 0, 2
                )
            },
            'monthly_trends': {
                'income': monthly_income,
                'expenses': monthly_expenses,
                'profit': [{
                    'month': m['month'],
                    'total': float(m['total'] or 0) - float(e['total'] or 0)
                } for m, e in zip(monthly_income, monthly_expenses)]
            },
            'categorical_data_year': {
                'expense_categories': [
                    {'name': cat['name'], 'value': cat['total']}
                    for cat in expense_categories_year if cat['total']
                ]
            },
            'categorical_data_month': {
                'expense_categories': [
                    {'name': cat['name'], 'value': cat['total']}
                    for cat in expense_categories_month if cat['total']
                ]
            },
            'asset_analysis': {
                'active_assets': asset_analysis.get('active', 0),
                'deprecated_assets': asset_analysis.get('deprecated', 0)
            },
            'additional_metrics': {
                'total_customers': Customer.objects.count(),
                'active_contractors': Contractors.objects.filter(is_still_active=True).count(),
                'active_employees': SalaryWorkers.objects.filter(is_still_active=True).count(),
                'inventory_items': InventoryItem.objects.count(),
                'raw_materials_types': RawMaterial.objects.count()
            }
        }

        return Response(data)