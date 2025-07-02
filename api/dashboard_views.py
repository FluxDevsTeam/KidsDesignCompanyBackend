from decimal import Decimal

from django.db import models

from rest_framework import viewsets
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Sum, Q, F, DecimalField
from django.db.models.functions import Coalesce
from dateutil.relativedelta import relativedelta
from customers.models import Customer
from expensis.models import Assets, ExpenseCategory, Expense
from products.models import ProductContractor, Product
from store.models import RawMaterial, Removed, AddRawMaterials
from shop.models import InventoryItem, Sold, AddStock
from datetime import timedelta
from workers.models import Contractors, SalaryWorkers, Paid
from project.models import Project, OtherProduction, OverheadCost
from .seralizers import SimpleCustomerSerializer
from .permissions import CheckUserRoles


class ApiStorekeeper(viewsets.ViewSet):
    permission_classes = [CheckUserRoles]
    required_roles = ['storekeeper', 'ceo']

    def list(self, request):
        today = timezone.now().date()
        start_month = today.replace(day=1)
        one_year_ago = today - timezone.timedelta(days=365)

        # modoels
        raw_materials = RawMaterial.objects.all()
        removed = Removed.objects.all()
        add_raw_material = AddRawMaterials.objects.all()

        total_raw_materials = raw_materials.count() or 0
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
                date__gte=month_start,
                date__lte=month_end
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
    permission_classes = [CheckUserRoles]
    required_roles = ['shopkeeper', 'ceo']

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
    permission_classes = [CheckUserRoles]
    required_roles = ['admin', 'ceo']

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


class ApiAccountantDashboard(viewsets.ViewSet):
    permission_classes = [CheckUserRoles]
    required_roles = ['accountant', 'ceo']

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
    permission_classes = [CheckUserRoles]
    required_roles = ['factory_manager', 'ceo']

    def list(self, request):
        today = timezone.now().date()
        start_of_year = today.replace(month=1, day=1)
        start_of_month = today.replace(day=1)
        assets = Assets.objects.all()
        expense = Expense.objects.all()
        sold = Sold.objects.all()
        project = Project.objects.all()
        paid = Paid.objects.all()
        customer = Customer.objects.all()
        all_salary_workers = SalaryWorkers.objects.all()
        all_contractors = Contractors.objects.all()
        product_contractor = ProductContractor.objects.all()
        add_raw_materials = AddRawMaterials.objects.all()
        other_production = OtherProduction.objects.all()

        # customer
        owing_customers = SimpleCustomerSerializer(customer.filter(project__balance__gte=1).distinct(), many=True).data
        owing_customers_count = customer.filter(project__balance__gte=1).distinct().count()
        all_customers = customer.count()
        all_active_customers = customer.filter(project__is_delivered=False).distinct().count()

        # Financial Metrics for the year
        total_shop_income_year = sold.filter(date__gte=start_of_year).aggregate(
            total=Sum(
                Coalesce(F('selling_price') * F('quantity'), Decimal('0')),
                output_field=DecimalField()
            )
        )['total'] or 0
        total_non_project_shop_income_year = sold.filter(project__isnull=True, date__gte=start_of_year).aggregate(
            total=Sum(
                Coalesce(F('selling_price') * F('quantity'), Decimal('0')),
                output_field=DecimalField()
            )
        )['total'] or 0

        total_projects_income_year = project.filter(start_date__gte=start_of_year).aggregate(
            total=Sum(
                Coalesce(F('selling_price'), Decimal('0')) +
                Coalesce(F('logistics'), Decimal('0')) +
                Coalesce(F('service_charge'), Decimal('0')),
                output_field=DecimalField()
            )
        )['total'] or 0
        no_shop_projects_income_year = project.filter(start_date__gte=start_of_year).aggregate(
            total=Sum(
                Coalesce(F('selling_price'), Decimal('0')) +
                Coalesce(F('logistics'), Decimal('0')) +
                Coalesce(F('service_charge'), Decimal('0')) -
                (total_shop_income_year - total_non_project_shop_income_year),
                output_field=DecimalField()
            )
        )['total'] or 0

        total_income_year = no_shop_projects_income_year + total_shop_income_year

        # Financial Health
        sales_count_this_month = sold.filter(date__month=today.month).count()
        total_project_sales_this_month = sold.filter(date__month=today.month, logistics=None).aggregate(
            total=Sum(
                Coalesce(F('selling_price') * F('quantity'), Decimal('0')),
                output_field=DecimalField()
            )
        )['total'] or 0
        total_non_project_sales_this_month = sold.filter(date__month=today.month, project=None).aggregate(
            total=Sum(
                Coalesce(F('selling_price') * F('quantity'), Decimal('0')),
                output_field=DecimalField()
            )
        )['total'] or 0
        total_sold_this_month = sold.filter(date__month=today.month).aggregate(
            total=Sum(
                Coalesce(F('selling_price') * F('quantity'), Decimal('0')),
                output_field=DecimalField()
            )
        )['total'] or 0
        total_sold_profit_this_month = sold.filter(date__month=today.month).aggregate(
            total=Sum(
                (Coalesce(F('selling_price'), Decimal('0')) * Coalesce(F('quantity'), 0)) -
                (Coalesce(F('cost_price'), Decimal('0')) * Coalesce(F('quantity'), 0)),
                output_field=DecimalField()
            )
        )['total'] or 0
        project_count_this_month = project.filter(start_date__month=today.month).count()
        total_project_amount_this_month = project.filter(start_date__month=today.month).aggregate(
            total=Sum(
                Coalesce(F('selling_price'), Decimal('0')) +
                Coalesce(F('logistics'), Decimal('0')) +
                Coalesce(F('service_charge'), Decimal('0')),
                output_field=DecimalField()
            )
        )['total'] or 0
        total_income_this_month = total_project_amount_this_month + (
            sold.filter(date__month=today.month, project=None).aggregate(
                total=Sum(
                    Coalesce(F('selling_price') * F('quantity'), Decimal('0')),
                    output_field=DecimalField()
                )
            )['total'] or 0
        )

        # Expenses Breakdown for the current month
        salary_costs_month = paid.filter(contract__isnull=True, date__gte=start_of_month).aggregate(total=Sum('amount'))['total'] or 0
        contractor_costs_month = product_contractor.filter(product__project__start_date__year=start_of_month.year, product__project__start_date__month=start_of_month.month).aggregate(total=Sum('cost'))['total'] or 0
        raw_material_costs_month = add_raw_materials.filter(date__year=start_of_month.year, date__month=start_of_month.month).aggregate(
            total=Sum(
                Coalesce(F('item__price') * F('quantity'), Decimal('0')),
                output_field=DecimalField()
            )
        )['total'] or 0
        asset_costs_month = assets.filter(date_added__year=start_of_month.year, date_added__month=start_of_month.month).aggregate(total=Sum('value'))['total'] or 0
        other_expenses_month = expense.filter(date__year=start_of_month.year, date__month=start_of_month.month).aggregate(total=Sum('amount'))['total'] or 0
        other_production_expensis_month = other_production.filter(project__start_date__gte=start_of_month).aggregate(total=Sum('cost'))['total'] or 0
        sold_cost_month = sold.filter(date__gte=start_of_month).aggregate(
            total=Sum(
                Coalesce(F('cost_price') * F('quantity'), Decimal('0')),
                output_field=DecimalField()
            )
        )['total'] or 0

        expenses_month = sum([sold_cost_month + salary_costs_month, contractor_costs_month, raw_material_costs_month, other_expenses_month + other_production_expensis_month])

        # Expenses Breakdown for the year
        salary_costs_year = paid.filter(contract__isnull=True, date__gte=start_of_year).aggregate(total=Sum('amount'))['total'] or 0
        contractor_costs_year = product_contractor.filter(product__project__start_date__gte=start_of_year).aggregate(total=Sum('cost'))['total'] or 0
        raw_material_costs_year = add_raw_materials.filter(date__gte=start_of_year).aggregate(
            total=Sum(
                Coalesce(F('item__price') * F('quantity'), Decimal('0')),
                output_field=DecimalField()
            )
        )['total'] or 0
        asset_costs_year = assets.filter(date_added__gte=start_of_year).aggregate(total=Sum('value'))['total'] or 0
        other_expenses_year = expense.filter(date__gte=start_of_year).aggregate(total=Sum('amount'))['total'] or 0
        other_production_expensis_year = other_production.filter(project__start_date__gte=start_of_year).aggregate(total=Sum('cost'))['total'] or 0
        sold_cost_year = sold.filter(date__gte=start_of_year).aggregate(
            total=Sum(
                Coalesce(F('cost_price') * F('quantity'), Decimal('0')),
                output_field=DecimalField()
            )
        )['total'] or 0
        total_expenses_year = sum([sold_cost_year + salary_costs_year, contractor_costs_year, raw_material_costs_year, other_expenses_year + other_production_expensis_year])

        # Calculate profit for the current month
        profit_month = total_income_this_month - expenses_month
        profit_year = total_income_year - total_expenses_year

        active_assets = assets.filter(is_still_available=True).aggregate(total=Sum('value'))['total'] or 0
        deprecated_assets = assets.filter(is_still_available=False).aggregate(total=Sum('value'))['total'] or 0

        categories = ExpenseCategory.objects.annotate(total=Sum('expense__amount')).filter(total__gt=0).order_by('-total')

        top_categories = categories[:4]
        others_total = sum(cat.total for cat in categories[4:])
        total_expenses_month = sum(cat.total for cat in categories)

        expensis_category_breakdown = []

        for cat in top_categories:
            percentage = ((cat.total / total_expenses_month) * 100) if total_expenses_month else 0
            expensis_category_breakdown.append({
                'category': cat.name,
                'total': cat.total,
                'percentage': round(percentage, 2)
            })

        if others_total > 0:
            others_percentage = ((others_total / total_expenses_month) * 100) if total_expenses_month else 0
            expensis_category_breakdown.append({
                'category': "Others",
                'total': others_total,
                'percentage': round(others_percentage, 2)
            })

        total_percentage = sum(item['percentage'] for item in expensis_category_breakdown)
        if expensis_category_breakdown and total_percentage != 100:
            difference = 100 - total_percentage
            expensis_category_breakdown[0]['percentage'] += difference

        # Monthly Trend with Others
        monthly_trend = []
        for i in range(12):
            month_start = (today.replace(day=1) - relativedelta(months=i))
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)

            month_total = expense.filter(date__gte=month_start, date__lte=month_end).aggregate(total=Sum('amount'))['total'] or 0

            project_total = expense.filter(project__isnull=False, date__range=[month_start, month_end]).aggregate(total=Sum('amount'))['total'] or 0

            shop_total = expense.filter(shop__isnull=False, date__range=[month_start, month_end]).aggregate(total=Sum('amount'))['total'] or 0

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

        monthly_trend_income = []
        for i in range(12):
            month_start = (today.replace(day=1) - relativedelta(months=i))
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)

            total_shop_income_year = sold.filter(date__gte=month_start, date__lte=month_end).aggregate(
                total=Sum(
                    Coalesce(F('selling_price') * F('quantity'), Decimal('0')),
                    output_field=DecimalField()
                )
            )['total'] or 0
            total_non_project_shop_income_year = sold.filter(project__isnull=True, date__gte=month_start, date__lte=month_end).aggregate(
                total=Sum(
                    Coalesce(F('selling_price') * F('quantity'), Decimal('0')),
                    output_field=DecimalField()
                )
            )['total'] or 0

            no_shop_projects_income_year = project.filter(start_date__gte=month_start, start_date__lte=month_end).aggregate(
                total=Sum(
                    Coalesce(F('selling_price'), Decimal('0')) +
                    Coalesce(F('logistics'), Decimal('0')) +
                    Coalesce(F('service_charge'), Decimal('0')) -
                    (total_shop_income_year - total_non_project_shop_income_year),
                    output_field=DecimalField()
                )
            )['total'] or 0

            month_total = total_shop_income_year + no_shop_projects_income_year

            monthly_trend_income.append({
                'month': month_start.strftime("%b %Y"),
                'total': float(month_total),
                'type_breakdown': {
                    'project': float(no_shop_projects_income_year),
                    'shop': float(total_shop_income_year),
                }
            })

        start_of_week = today - timezone.timedelta(days=today.weekday())
        # Top 5 Categories
        top_categories = ExpenseCategory.objects.annotate(total=Sum('expense__amount')).filter(total__gt=0).order_by('-total')[:5].values('name', 'total')
        monthly_total_paid = paid.filter(date__month=today.month).aggregate(Sum('amount'))['amount__sum'] or 0.0
        weekly_total_paid = paid.filter(date__range=[start_of_week, today]).aggregate(Sum('amount'))['amount__sum'] or 0.0

        salary_workers_count = all_salary_workers.count()
        active_salary_workers_count = all_salary_workers.filter(is_still_active=True).count()
        total_salary_workers_monthly_pay = all_salary_workers.aggregate(total=Sum('salary'))['total'] or 0.0
        total_paid = all_salary_workers.filter(paid__date__month=today.month).aggregate(total=Sum('paid__amount'))['total'] or 0.0

        all_contractors_count = all_contractors.count()
        all_active_contractors_count = all_contractors.filter(is_still_active=True).count()

        total_contractors_monthly_pay = all_contractors.filter(paid__date__month=today.month).aggregate(total=Sum('paid__amount'))['total'] or 0.0
        total_contractors_weekly_pay = all_contractors.filter(paid__date__range=(start_of_week, today)).aggregate(total=Sum('paid__amount'))['total'] or 0.0

        data = {
            'financial_health': {
                'active_assets': active_assets,
                'deprecated_assets': deprecated_assets,
                'sales_count_this_month': sales_count_this_month,
                'total_project_sales_this_month': total_project_sales_this_month,
                'total_non_project_sales_this_month': total_non_project_sales_this_month,
                'total_shop_items_sold_this_month': total_sold_this_month,
                'total_shop_profit_this_month': total_sold_profit_this_month,
                'project_count_this_month': project_count_this_month,
                'total_project_amount_this_month': total_project_amount_this_month,
                'total_income_this_month': total_income_this_month,
                'total_expenses_month': expenses_month,
                'profit_month': profit_month
            },
            'yearly_data': {
                'total_expenses_year': total_expenses_year,
                'total_income_year': total_income_year,
                'profit_year': profit_year,
            },
            'customers': {
                'all_customers_count': all_customers,
                'active_customers_count': all_active_customers,
                'owing_customers_count': owing_customers_count,
                'owing_customers': owing_customers
            },
            'workers': {
                'salary_workers_count': salary_workers_count,
                'active_salary_workers_count': active_salary_workers_count,
                'total_salary_workers_monthly_pay': total_salary_workers_monthly_pay,
                'all_contractors_count': all_contractors_count,
                'all_active_contractors_count': all_active_contractors_count,
            },
            'paid': {
                'monthly_total_paid': monthly_total_paid,
                'weekly_total_paid': weekly_total_paid,
                'total_paid': total_paid,
                'total_contractors_monthly_pay': total_contractors_monthly_pay,
                'total_contractors_weekly_pay': total_contractors_weekly_pay,
            },
            'expense_category_breakdown': expensis_category_breakdown,
            'monthly_expense_trend': list(reversed(monthly_trend)),
            'monthly_income_trend': list(reversed(monthly_trend_income)),
            'top_categories': top_categories,
        }
        return Response(data)


class CEODashboardViewSet(viewsets.ViewSet):
    permission_classes = [CheckUserRoles]
    required_roles = ['ceo']

    def list(self, request):
        today = timezone.now().date()
        start_of_year = today.replace(month=1, day=1)
        start_of_month = today.replace(day=1)

        # Set variables at the top

        assets = Assets.objects.all()
        expense = Expense.objects.all()
        sold = Sold.objects.all()
        project = Project.objects.all()
        paid = Paid.objects.all()
        customer = Customer.objects.all()
        all_salary_workers = SalaryWorkers.objects.all()
        all_contractors = Contractors.objects.all()
        product_contractor = ProductContractor.objects.all()
        add_raw_materials = AddRawMaterials.objects.all()
        other_production = OtherProduction.objects.all()
        inventory_item = InventoryItem.objects.all()
        raw_material = RawMaterial.objects.all()
        expense_category = ExpenseCategory.objects.all()

        # Helper function for monthly aggregates
        def get_monthly_data(model, date_field, value_field):
            monthly_data = []
            for i in range(12):
                month_start = (today.replace(day=1) - relativedelta(months=i))
                month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
                total = model.filter(
                    **{f"{date_field}__gte": month_start, f"{date_field}__lte": month_end}
                ).aggregate(total=Sum(value_field))['total'] or 0
                monthly_data.append({
                    'month': month_start.strftime("%b %Y"),
                    'total': float(total)
                })
            return list(reversed(monthly_data))

        # Financial Metrics for the year
        total_shop_income_year = sold.filter(date__gte=start_of_year).aggregate(total=Sum(F('selling_price') * F('quantity')))['total'] or 0
        total_non_project_shop_income_year = sold.filter(project__isnull=True, date__gte=start_of_year).aggregate(total=Sum(F('selling_price') * F('quantity')))['total'] or 0

        total_projects_income_year = project.filter(start_date__gte=start_of_year).aggregate(total=Sum(F('selling_price') + F('logistics') + F('service_charge')))['total'] or 0
        no_shop_projects_income_year = project.filter(start_date__gte=start_of_year).aggregate(total=Sum(F('selling_price') + F('logistics') + F('service_charge') - (total_shop_income_year -total_non_project_shop_income_year)))['total'] or 0

        total_income_year = no_shop_projects_income_year + total_shop_income_year

        # Financial Metrics for the current month
        total_shop_income_month = sold.filter(project__isnull=True, date__gte=start_of_month).aggregate(total=Sum(F('selling_price') * F('quantity')))['total'] or 0
        total_non_project_shop_income_month = sold.filter(project__isnull=True, date__gte=start_of_month).aggregate(total=Sum(F('selling_price') * F('quantity')))['total'] or 0

        total_projects_income_month = project.filter(start_date__gte=start_of_month).aggregate(total=Sum(F('selling_price') + F('logistics') + F('service_charge')))['total'] or 0
        no_shop_projects_income_month = project.filter(start_date__gte=start_of_month).aggregate(total=Sum(F('selling_price') + F('logistics') + F('service_charge') - (total_shop_income_year -total_non_project_shop_income_year)))['total'] or 0

        total_income_month = no_shop_projects_income_month + total_shop_income_month

        # Expenses Breakdown for the year
        salary_costs_year = paid.filter(contract__isnull=True, date__gte=start_of_year).aggregate(total=Sum('amount'))['total'] or 0

        contractor_costs_year = product_contractor.filter(product__project__start_date__gte=start_of_year).aggregate(total=Sum('cost'))['total'] or 0

        raw_material_costs_year = add_raw_materials.filter(date__gte=start_of_year).aggregate(total=Sum(F('item__price') * F('quantity')))['total'] or 0

        asset_costs_year = assets.filter(date_added__gte=start_of_year).aggregate(total=Sum('value'))['total'] or 0

        other_expenses_year = expense.filter(date__gte=start_of_year).aggregate(total=Sum('amount'))['total'] or 0

        other_production_expensis_year = other_production.filter(project__start_date__gte=start_of_year).aggregate(total=Sum('cost'))['total'] or 0

        sold_cost_year = sold.filter(date__gte=start_of_year).aggregate(total=Sum(F('cost_price') * F('quantity')))['total'] or 0

        total_expenses_year = sum([sold_cost_year + salary_costs_year, contractor_costs_year, raw_material_costs_year, other_expenses_year + other_production_expensis_year])

        # Expenses Breakdown for the current month
        salary_costs_month = paid.filter(contract__isnull=True, date__gte=start_of_month).aggregate(total=Sum('amount'))['total'] or 0

        contractor_costs_month = product_contractor.filter(product__project__start_date__year=start_of_month.year, product__project__start_date__month=start_of_month.month).aggregate(total=Sum('cost'))['total'] or 0

        raw_material_costs_month = add_raw_materials.filter(date__year=start_of_month.year, date__month=start_of_month.month).aggregate(total=Sum(F('item__price') * F('quantity')))['total'] or 0

        asset_costs_month = assets.filter(date_added__year=start_of_month.year, date_added__month=start_of_month.month).aggregate(total=Sum('value'))['total'] or 0

        other_expenses_month = expense.filter(date__year=start_of_month.year, date__month=start_of_month.month).aggregate(total=Sum('amount'))['total'] or 0

        other_production_expensis_month = other_production.filter(project__start_date__gte=start_of_month).aggregate(total=Sum('cost'))['total'] or 0

        sold_cost_month = sold.filter(date__gte=start_of_month).aggregate(total=Sum(F('cost_price') * F('quantity')))['total'] or 0

        total_expenses_month = sum([sold_cost_month + salary_costs_month, contractor_costs_month, raw_material_costs_month, other_expenses_month + other_production_expensis_month])

        # Profit Calculations for the year
        profit_year = total_income_year - total_expenses_year

        # Profit Calculations for the current month
        profit_month = total_income_month - total_expenses_month

        # Inventory Value
        inventory_value = inventory_item.aggregate(total=Sum(F('stock') * F('selling_price')))['total'] or 0

        # Store Value
        total_store_value = raw_material.aggregate(total=Sum(F('quantity') * F('price')))['total'] or 0

        # Monthly Trends
        monthly_income = get_monthly_data(sold, 'date', F('selling_price') * F('quantity'))
        factory_expenses_month = expense.filter(date__year=start_of_month.year, date__month=start_of_month.month, project__isnull=True, shop__isnull=True ).aggregate(total=Sum('amount'))['total'] or 0
        suggested_overhead_cost = (salary_costs_month + factory_expenses_month) / 26 # 26 is the number of working days in a month

        monthly_expenses = []
        for i in range(12):
            month_start = today.replace(day=1) - relativedelta(months=i)
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)

            expenses = {
                'salary': paid.filter(contract__isnull=True, date__month=month_start.month, date__year=month_start.year).aggregate(total=Sum('amount'))['total'] or 0,
                'contractors': ProductContractor.objects.filter(product__project__start_date__year=month_start.year, product__project__start_date__month=month_start.month).aggregate(total=Sum('cost'))['total'] or 0,
                'materials': AddRawMaterials.objects.filter(date__year=month_start.year,date__month=month_start.month).aggregate(total=Sum(F('item__price') * F('quantity')))['total'] or 0,
                'other_expensis': expense.filter(date__year=month_start.year, date__month=month_start.month).aggregate(total=Sum('amount'))['total'] or 0,
                'other_production_expensis': OtherProduction.objects.filter(project__start_date__year=month_start.year, project__start_date__month=month_start.month).aggregate(total=Sum('cost'))['total'] or 0,
                'sold_cost': sold.filter(date__year=month_start.year, date__month=month_start.month).aggregate(total=Sum(F('cost_price') * F('quantity')))['total'] or 0
            }

            total_expenses = sum(expenses.values())
            monthly_expenses.append({
                'month': month_start.strftime("%b %Y"),
                'total': total_expenses,
            })

        monthly_expenses.reverse()

        # Categorical Breakdowns for the year
        expense_categories_year = expense_category.filter(expense__date__gte=start_of_year).annotate(total=Sum('expense__amount')).values('name', 'total').order_by('-total')

        # Categorical Breakdowns for the month
        expense_categories_month = expense_category.annotate(total=Sum('expense__amount', filter=Q(expense__date__gte=start_of_month))).values('name', 'total').order_by('-total')

        # Asset Analysis
        asset_analysis = assets.aggregate(active=Sum('value', filter=Q(is_still_available=True)), deprecated=Sum('value', filter=Q(is_still_available=False))) or 0

        # Customer Analysis
        owing_customers = SimpleCustomerSerializer(customer.filter(project__balance__gte=1).distinct(), many=True).data
        owing_customers_count = customer.filter(project__balance__gte=1).distinct().count()
        all_customers = customer.count()
        all_active_customers = customer.filter(project__is_delivered=False).distinct().count()

        # Worker Analysis
        total_salary_workers = all_salary_workers.count()
        active_salary_workers = all_salary_workers.filter(is_still_active=True).count()
        total_contractors = all_contractors.count()
        active_contractors = all_contractors.filter(is_still_active=True).count()

        data = {
            'key_metrics': {
                'overhead_cost': OverheadCost.objects.first().overhead_cost_base,
                'suggested_overhead_cost': round(suggested_overhead_cost),
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
            'customers': {
                "all_customers_count": all_customers,
                "active_customers_count": all_active_customers,
                'owing_customers_count': owing_customers_count,
                'owing_customers': owing_customers
            },
            'additional_metrics': {
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
    permission_classes = [CheckUserRoles]
    required_roles = ['project_manager', 'ceo']

    def list(self, request):
        today = timezone.now().date()
        start_of_year = today.replace(month=1, day=1)
        start_of_month = today.replace(day=1)

        # Set variables at the top
        assets = Assets.objects.all()
        expense = Expense.objects.all()
        sold = Sold.objects.all()
        project = Project.objects.all()
        product = Product.objects.all()
        paid = Paid.objects.all()
        product_contractor = ProductContractor.objects.all()
        add_raw_materials = AddRawMaterials.objects.all()
        other_production = OtherProduction.objects.all()
        customer = Customer.objects.all()

        # Helper function for monthly aggregates
        def get_monthly_data(model, date_field, value_field):
            monthly_data = []
            for i in range(12):
                month_start = today.replace(day=1) - relativedelta(months=i)
                month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
                total = model.filter(
                    **{f"{date_field}__gte": month_start, f"{date_field}__lte": month_end}
                ).aggregate(total=Sum(value_field))['total'] or 0
                monthly_data.append({
                    'month': month_start.strftime("%b %Y"),
                    'total': float(total)
                })
            return list(reversed(monthly_data))

        # Financial Metrics for the year
        total_project_shop_income_year = sold.filter(project__isnull=False, date__gte=start_of_year).aggregate(total=Sum(F('selling_price') * F('quantity')))['total'] or 0

        total_projects_count_year = project.filter(start_date__gte=start_of_year).count()
        total_projects_income_year = project.filter(start_date__gte=start_of_year).aggregate(total=Sum(F('selling_price') + F('logistics') + F('service_charge')))['total'] or 0
        no_shop_projects_income_year = project.filter(start_date__gte=start_of_year).aggregate(total=Sum(F('selling_price') + F('logistics') + F('service_charge') - total_project_shop_income_year))['total'] or 0


        # Financial Metrics for the current month
        total_project_shop_income_month = sold.filter(project__isnull=False, date__gte=start_of_month).aggregate(total=Sum(F('selling_price') * F('quantity')))['total'] or 0

        total_projects_count_month = project.filter(start_date__gte=start_of_month).count()
        total_projects_income_month = project.filter(start_date__gte=start_of_month).aggregate(total=Sum(F('selling_price') + F('logistics') + F('service_charge')))['total'] or 0
        no_shop_projects_income_month = project.filter(start_date__gte=start_of_month).aggregate(total=Sum(F('selling_price') + F('logistics') + F('service_charge') - total_project_shop_income_month))['total'] or 0


        # Expenses Breakdown for the year

        contractor_costs_year = product_contractor.filter(product__project__start_date__gte=start_of_year).aggregate(total=Sum('cost'))['total'] or 0

        raw_material_costs_year = add_raw_materials.filter(date__gte=start_of_year).aggregate(total=Sum(F('item__price') * F('quantity')))['total'] or 0

        overhead_cost_year = product.filter(project__start_date__gte=start_of_year).aggregate(total=Coalesce(Sum(F("overhead_cost") * F("overhead_cost_base_at_creation")), Decimal(0)))["total"]

        expenses_year = expense.filter(date__gte=start_of_year, project__isnull=False).aggregate(total=Sum('amount'))['total'] or 0

        other_production_expensis_year = other_production.filter(project__start_date__gte=start_of_year).aggregate(total=Sum('cost'))['total'] or 0

        sold_cost_year = sold.filter(date__gte=start_of_year, project__isnull=False).aggregate(total=Sum(F('cost_price') * F('quantity')))['total'] or 0

        total_project_expenses_year = sum([overhead_cost_year + sold_cost_year, contractor_costs_year, raw_material_costs_year, expenses_year + other_production_expensis_year])

        # Profit Calculations for the year
        profit_year = total_projects_income_year - total_project_expenses_year

        # Expenses Breakdown for the current month
        contractor_costs_month = product_contractor.filter(product__project__start_date__gte=start_of_month).aggregate(total=Sum('cost'))['total'] or 0

        raw_material_costs_month = add_raw_materials.filter(date__gte=start_of_month).aggregate(total=Sum(F('item__price') * F('quantity')))['total'] or 0

        overhead_cost_month = product.filter(project__start_date__gte=start_of_month).aggregate(total=Coalesce(Sum(F("overhead_cost") * F("overhead_cost_base_at_creation")), Decimal(0)))["total"]

        expenses_month = expense.filter(date__gte=start_of_month, project__isnull=False).aggregate(total=Sum('amount'))['total'] or 0

        other_production_expensis_month = other_production.filter(project__start_date__gte=start_of_month).aggregate(total=Sum('cost'))['total'] or 0

        sold_cost_month = sold.filter(date__gte=start_of_month, project__isnull=False).aggregate(total=Sum(F('cost_price') * F('quantity')))['total'] or 0

        total_project_expenses_month = sum([overhead_cost_month + sold_cost_month, contractor_costs_month, raw_material_costs_month, expenses_month + other_production_expensis_month])

        # Profit Calculations for the current month
        profit_month = total_projects_income_month - total_project_expenses_month

        # Monthly Trends
        monthly_income = get_monthly_data(project, 'start_date', F('selling_price') + F('logistics') + F('service_charge'))

        monthly_expenses = []
        for i in range(12):
            month_start = today.replace(day=1) - relativedelta(months=i)
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)

            contractor_costs_month = product_contractor.filter(product__project__start_date__year=month_start.year,product__project__start_date__month=month_start.month).aggregate(total=Sum('cost'))['total'] or 0

            raw_material_costs_month = add_raw_materials.filter(date__year=month_start.year,date__month=month_start.month).aggregate(total=Sum(F('item__price') * F('quantity')))['total'] or 0

            overhead_cost_month = product.filter(project__start_date__year=month_start.year, project__start_date__month=month_start.month, ).aggregate(total=Coalesce(Sum(F("overhead_cost") * F("overhead_cost_base_at_creation")), Decimal(0)))["total"]

            expenses_month = expense.filter(date__year=month_start.year,date__month=month_start.month, project__isnull=False).aggregate(total=Sum('amount'))['total'] or 0

            other_production_expensis_month = other_production.filter( project__start_date__year=month_start.year, project__start_date__month=month_start.month).aggregate(total=Sum('cost'))['total'] or 0

            sold_cost_month = sold.filter(date__year=month_start.year,date__month=month_start.month, project__isnull=False).aggregate(total=Sum(F('cost_price') * F('quantity')))['total'] or 0

            total_project = sum([overhead_cost_month + sold_cost_month, contractor_costs_month, raw_material_costs_month,expenses_month + other_production_expensis_month])

            monthly_expenses.append({
                'month': month_start.strftime("%b %Y"),
                'total': total_project,
            })

        monthly_expenses.reverse()
        owing_customers = SimpleCustomerSerializer(customer.filter(project__balance__gte=1).distinct(), many=True).data
        owing_customers_count = customer.filter(project__balance__gte=1).distinct().count()
        all_customers = customer.count()
        all_active_customers = customer.filter(project__is_delivered=False).distinct().count()

        data = {
            'key_metrics': {
                'overhead_cost': OverheadCost.objects.first().overhead_cost_base,
            },
            'breakdown_year': {
                'projects_count_year': round(total_projects_count_year, 2),
                'total_projects_income_year': round(total_projects_income_year, 2),
                'no_shop_projects_year': round(no_shop_projects_income_year, 2),
                'project_shop_income_year': round(total_project_shop_income_year, 2),
                'percentage_projects': round((no_shop_projects_income_year / total_projects_income_year * 100) if total_projects_income_year else 0, 2),
                'percentage_shop': round((total_project_shop_income_year / total_projects_income_year * 100) if total_projects_income_year else 0, 2),
                'project_expenses_year': round(total_project_expenses_year, 2),
                'profit_year': round(profit_year, 2),
            },
            'breakdown_month': {
                'projects_count_month': round(total_projects_count_month, 2),
                'total_projects_income_month': round(total_projects_income_month, 2),
                'no_shop_projects_month': round(no_shop_projects_income_month, 2),
                'project_shop_income_month': round(total_project_shop_income_month, 2),
                'percentage_projects': round((no_shop_projects_income_month / total_projects_income_month * 100) if total_projects_income_month else 0,2),
                'percentage_shop': round((total_project_shop_income_month / total_projects_income_month * 100) if total_projects_income_month else 0,2),
                'project_expenses_month': round(total_project_expenses_month, 2),
                'profit_month': round(profit_month, 2),
            },
            'expense_breakdown_year': {
                'contractors': round(contractor_costs_year, 2),
                'raw_materials': round(raw_material_costs_year, 2),
                'overhead': round(overhead_cost_year, 2),
                'factory_expenses': round(expenses_year, 2),
                'other_production_expensis': round(other_production_expensis_year, 2),
                'sold_cost': round(sold_cost_year, 2),
                'yearly_sold_cost_price': round(sold_cost_year, 2),
                'total_project_expenses_year': round(total_project_expenses_year, 2),
            },
            'expense_breakdown_month': {
                'contractors': round(contractor_costs_month, 2),
                'raw_materials': round(raw_material_costs_month, 2),
                'overhead': round(overhead_cost_month, 2),
                'factory_expenses': round(expenses_month, 2),
                'other_production_expensis': round(other_production_expensis_month, 2),
                'sold_cost': round(sold_cost_month, 2),
                'monthly_sold_cost_price': round(sold_cost_month, 2),
                'total_project_expenses_month': round(total_project_expenses_month, 2),
            },
            'monthly_trends': {
                'income': monthly_income,
                'expenses': monthly_expenses,
                'profit': [{
                    'month': m['month'],
                    'total': float(m['total'] or 0) - float(e['total'] or 0)
                } for m, e in zip(monthly_income, monthly_expenses)]
            },
            'customers': {
                "all_customers_count": all_customers,
                "active_customers_count": all_active_customers,
                'owing_customers_count': owing_customers_count,
                'owing_customers': owing_customers
            },
            'additional_metrics': {
                'active_employees': SalaryWorkers.objects.filter(is_still_active=True).count() + Contractors.objects.filter(is_still_active=True).count(),
            }
        }

        return Response(data)
