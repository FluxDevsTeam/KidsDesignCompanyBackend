from rest_framework import viewsets
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Sum, Q, F, Count, Subquery, OuterRef, FloatField, Prefetch, ExpressionWrapper
from django.db.models.functions import Coalesce

from api.dashboard_serializers import CustomerDashboardSerializer, CEODashboardSerializer
from customers.models import Customer
from expensis.models import Assets, ExpenseCategory, Expense
from products.models import ProductContractor, Product
from store.models import RawMaterial, Removed, AddRawMaterials
from shop.models import InventoryItem, Sold, AddStock
from datetime import timedelta
from workers.models import Contractors, SalaryWorkers
from project.models import Project, OtherProduction


class RawMaterialDashboardViewSet(viewsets.ViewSet):
    def list(self, request):
        today = timezone.now().date()
        start_week = today - timezone.timedelta(days=today.weekday())
        start_month = today.replace(day=1)
        one_year_ago = today - timezone.timedelta(days=365)

        total_raw_materials = RawMaterial.objects.aggregate(total=Sum('quantity'))['total'] or 0
        total_value = RawMaterial.objects.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
        removed_cost_today = Removed.objects.filter(date=today).aggregate(total=Sum('price'))['total'] or 0
        removed_cost_week = Removed.objects.filter(date__gte=start_week).aggregate(total=Sum('price'))['total'] or 0
        removed_cost_month = Removed.objects.filter(date__gte=start_month).aggregate(total=Sum('price'))['total'] or 0
        removed_amount_year = \
        Removed.objects.filter(date__gte=one_year_ago).aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
        added_amount_year = \
        AddRawMaterials.objects.filter(date__gte=one_year_ago).aggregate(total=Sum(F('item__price') * F('quantity')))[
            'total'] or 0

        monthly_added = []
        monthly_removed = []

        for i in range(12):
            month_start = today.replace(day=1) - timezone.timedelta(days=30 * i)
            month_end = (month_start + timezone.timedelta(days=32)).replace(day=1) - timezone.timedelta(days=1)

            added_total = AddRawMaterials.objects.filter(
                date__date__gte=month_start,
                date__date__lte=month_end
            ).aggregate(total=Sum(F('item__price') * F('quantity')))['total'] or 0

            removed_total = Removed.objects.filter(
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

        data = {
            'total_raw_materials': total_raw_materials,
            'total_value': total_value,
            'removed_cost_today': removed_cost_today,
            'removed_cost_week': removed_cost_week,
            'removed_cost_month': removed_cost_month,
            'removed_amount_year': removed_amount_year,
            'added_amount_year': added_amount_year,
            'added_amount_monthly': monthly_added,
            'removed_amount_monthly': monthly_removed
        }

        return Response(data)


class InventoryDashboardViewSet(viewsets.ViewSet):
    def list(self, request):
        today = timezone.now().date()
        one_year_ago = today - timezone.timedelta(days=365)
        current_month_start = today.replace(day=1)
        next_month = today.replace(day=28) + timezone.timedelta(days=4)
        current_month_end = next_month - timezone.timedelta(days=next_month.day)

        # Current totals
        total_shop_value = InventoryItem.objects.aggregate(
            total=Sum(F('stock') * F('selling_price'))
        )['total'] or 0

        total_cost_value = InventoryItem.objects.aggregate(
            total=Sum(F('stock') * F('cost_price'))
        )['total'] or 0

        total_profit_potential = InventoryItem.objects.aggregate(
            total=Sum((F('selling_price') - F('cost_price')) * F('stock'))
        )['total'] or 0

        # Yearly aggregates
        yearly_profit = Sold.objects.filter(date__gte=one_year_ago).aggregate(
            total=Sum((F('selling_price') - F('cost_price')) * F('quantity'))
        )['total'] or 0

        yearly_added_value = AddStock.objects.filter(date__gte=one_year_ago).aggregate(
            total=Sum(F('item__cost_price') * F('quantity'))
        )['total'] or 0

        # Current month aggregates
        total_sold_this_month = Sold.objects.filter(
            date__gte=current_month_start,
            date__lte=current_month_end
        ).aggregate(
            total=Sum(F('selling_price') * F('quantity'))
        )['total'] or 0

        total_added_this_month = AddStock.objects.filter(
            date__gte=current_month_start,
            date__lte=current_month_end
        ).aggregate(
            total=Sum(F('item__cost_price') * F('quantity'))
        )['total'] or 0

        total_profit_this_month = Sold.objects.filter(
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
            month_start = today.replace(day=1) - timezone.timedelta(days=30*i)
            month_end = (month_start + timezone.timedelta(days=32)).replace(day=1) - timezone.timedelta(days=1)

            # Monthly profit
            month_profit = Sold.objects.filter(
                date__gte=month_start,
                date__lte=month_end
            ).aggregate(
                total=Sum((F('selling_price') - F('cost_price')) * F('quantity'))
            )['total'] or 0

            # Monthly added stock value
            month_added = AddStock.objects.filter(
                date__gte=month_start,
                date__lte=month_end
            ).aggregate(
                total=Sum(F('item__cost_price') * F('quantity'))
            )['total'] or 0

            # Monthly sales value
            month_sold = Sold.objects.filter(
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

        data = {
            'total_shop_value': total_shop_value,
            'total_cost_value': total_cost_value,
            'total_profit_potential': total_profit_potential,
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


class WorkersDashboardViewSet(viewsets.ViewSet):
    def list(self, request):
        today = timezone.now().date()
        one_year_ago = today - timedelta(days=365)
        current_month_start = today.replace(day=1)
        next_month = today.replace(day=28) + timedelta(days=4)
        current_month_end = next_month - timedelta(days=next_month.day)

        # Contractors data
        contractors = []
        all_contractor_payments = []

        for contractor in Contractors.objects.all():
            contracts = ProductContractor.objects.filter(contractor=contractor)
            total_pay = contracts.aggregate(t=Sum('cost'))['t'] or 0

            last_month_pay = contracts.filter(
                product__project__start_date__gte=current_month_start - timedelta(days=30),
                product__project__start_date__lte=current_month_end - timedelta(days=30)
            ).aggregate(t=Sum('cost'))['t'] or 0

            last_year_pay = contracts.filter(
                product__project__start_date__gte=one_year_ago
            ).aggregate(t=Sum('cost'))['t'] or 0

            monthly_payments = []
            for i in range(12):
                month_start = today.replace(day=1) - timedelta(days=30 * i)
                month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                monthly_total = contracts.filter(
                    product__project__start_date__gte=month_start,
                    product__project__start_date__lte=month_end
                ).aggregate(t=Sum('cost'))['t'] or 0
                monthly_payments.append({'month': month_start.strftime("%b %Y"), 'amount': float(monthly_total)})

            projects = Project.objects.filter(
                product__productcontractor__contractor=contractor
            ).distinct().values('id', 'name', 'status', 'start_date')

            contractors.append({
                'id': contractor.id,
                'full_name': f"{contractor.first_name} {contractor.last_name}",
                'total_pay': total_pay,
                'last_month_pay': last_month_pay,
                'last_year_pay': last_year_pay,
                'monthly_payments': list(reversed(monthly_payments)),
                'projects': list(projects)
            })

        # Salary workers data
        salary_workers = []
        for worker in SalaryWorkers.objects.all():
            projects = Project.objects.filter(
                product__productsalaryworker__salary_worker=worker
            ).distinct().values('id', 'name', 'status', 'start_date')

            salary_workers.append({
                'id': worker.id,
                'full_name': f"{worker.first_name} {worker.last_name}",
                'pay': float(worker.salary),
                'projects': list(projects)
            })

        # Salary costs (total of all salaries)
        salary_costs = sum(worker.salary for worker in SalaryWorkers.objects.all())

        # Contractors monthly payments
        contractors_monthly = []
        for i in range(12):
            month_start = today.replace(day=1) - timedelta(days=30 * i)
            month_total = ProductContractor.objects.filter(
                product__project__start_date__gte=month_start,
                product__project__start_date__lte=(month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            ).aggregate(t=Sum('cost'))['t'] or 0
            contractors_monthly.append({
                'month': month_start.strftime("%b %Y"),
                'amount': float(month_total)
            })

        # Current month contractor payments
        current_month_contractor_payments = ProductContractor.objects.filter(
            product__project__start_date__gte=current_month_start,
            product__project__start_date__lte=current_month_end
        ).aggregate(t=Sum('cost'))['t'] or 0

        # Total monthly cost
        total_monthly_cost = salary_costs + current_month_contractor_payments

        return Response({
            'contractors': contractors,
            'salary_workers': salary_workers,
            'contractors_monthly': list(reversed(contractors_monthly)),
            'salary_costs': float(salary_costs),
            'current_month_contractor_payments': float(current_month_contractor_payments),
            'total_monthly_cost': float(total_monthly_cost)
        })


class ExpenseDashboardViewSet(viewsets.ViewSet):
    def list(self, request):
        today = timezone.now().date()

        # Financial Health
        total_expenses = Expense.objects.aggregate(total=Sum('amount'))['total'] or 0
        active_assets = Assets.objects.filter(is_still_available=True).aggregate(total=Sum('value'))['total'] or 0
        deprecated_assets = Assets.objects.filter(is_still_available=False).aggregate(total=Sum('value'))['total'] or 0

        # Category Breakdown with Percentage
        categories = ExpenseCategory.objects.annotate(
            total=Sum('expense__amount')
        ).filter(total__gt=0).order_by('-total')

        category_breakdown = []
        for cat in categories:
            percentage = (cat.total / total_expenses * 100) if total_expenses else 0
            category_breakdown.append({
                'category': cat.name,
                'total': cat.total,
                'percentage': round(percentage, 2)
            })

        # Monthly Trend with Others
        monthly_trend = []
        for i in range(12):
            month_start = today.replace(day=1) - timedelta(days=30 * i)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            month_total = Expense.objects.filter(
                date__gte=month_start,
                date__lte=month_end
            ).aggregate(total=Sum('amount'))['total'] or 0

            project_total = Expense.objects.filter(
                project__isnull=False,
                date__range=[month_start, month_end]
            ).aggregate(total=Sum('amount'))['total'] or 0

            shop_total = Expense.objects.filter(
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

        # Top 5 Categories
        top_categories = ExpenseCategory.objects.annotate(
            total=Sum('expense__amount')
        ).filter(total__gt=0).order_by('-total')[:5].values('name', 'total')

        # Asset Lifespan Analysis
        asset_lifespan = Assets.objects.annotate(
            lifespan_years=F('expected_lifespan')
        ).values('name', 'value', 'lifespan_years', 'is_still_available')

        data = {
            'financial_health': {
                'total_expenses': total_expenses,
                'active_assets': active_assets,
                'deprecated_assets': deprecated_assets
            },
            'category_breakdown': category_breakdown,
            'monthly_trend': list(reversed(monthly_trend)),
            'top_categories': top_categories,
            'asset_lifespan': asset_lifespan
        }

        return Response(data)


class CustomerDashboardViewSet(viewsets.ViewSet):
    def list(self, request):
        # Optimized database queries
        customers = Customer.objects.prefetch_related(
            Prefetch('project_set', queryset=Project.objects.only(
                'id', 'name', 'status', 'start_date', 'balance',
                'selling_price', 'logistics', 'service_charge'
            )),
            Prefetch('sold_set', queryset=Sold.objects.select_related('item').only(
                'id', 'quantity', 'selling_price', 'date',
                'item__name', 'customer_id'
            ))
        ).all()

        all_customers = []
        owing_customers = []

        for customer in customers:
            # Process projects
            projects = []
            total_balance = 0.0

            for project in customer.project_set.all():
                project_balance = float(project.balance)
                total_balance += project_balance

                projects.append({
                    'id': project.id,
                    'name': project.name,
                    'status': project.status,
                    'start_date': project.start_date,
                    'total_paid': float(project.selling_price + project.logistics + project.service_charge),
                    'balance': project_balance,
                    'is_owing': project_balance > 0
                })

            # Process shop items
            shop_items = []
            for sold in customer.sold_set.all():
                shop_items.append({
                    'id': sold.id,
                    'item_name': sold.item.name,
                    'quantity': float(sold.quantity),
                    'selling_price': float(sold.selling_price),
                    'total_paid': float(sold.quantity * sold.selling_price),
                    'date': sold.date
                })

            project_total = sum(p['total_paid'] for p in projects)
            shop_total = sum(s['total_paid'] for s in shop_items)

            customer_data = {
                'id': customer.id,
                'name': customer.name,
                'email': customer.email,
                'phone_number': customer.phone_number,
                'projects': projects,
                'shop_items': shop_items,
                'total_spent': round(project_total + shop_total, 2),
                'total_balance': round(total_balance, 2),
                'is_owing': total_balance > 0
            }

            all_customers.append(customer_data)
            if customer_data['is_owing']:
                owing_customers.append(customer_data)

        # Build final response
        response_data = {
            'total_customers': len(all_customers),
            'all_customers': all_customers,
            'owing_customers': {
                'count': len(owing_customers),
                'total_balance': round(sum(c['total_balance'] for c in owing_customers), 2),
                'customers': owing_customers
            }
        }

        # Validate response structure
        serializer = CustomerDashboardSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)


class CEODashboardViewSet(viewsets.ViewSet):
    def list(self, request):
        today = timezone.now().date()
        one_year_ago = today - timedelta(days=365)

        # Helper function for monthly aggregates
        def get_monthly_data(model, date_field, value_field):
            monthly_data = []
            for i in range(12):
                month_start = today.replace(day=1) - timedelta(days=30 * i)
                month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                total = model.objects.filter(
                    **{f"{date_field}__gte": month_start, f"{date_field}__lte": month_end}
                ).aggregate(total=Sum(value_field))['total'] or 0
                monthly_data.append({
                    'month': month_start.strftime("%b %Y"),
                    'total': float(total)
                })
            return list(reversed(monthly_data))

        # Financial Metrics
        total_projects_income = Project.objects.aggregate(
            total=Sum(F('selling_price') + F('logistics') + F('service_charge'))
        )['total'] or 0

        total_shop_income = Sold.objects.filter(project__isnull=True).aggregate(
            total=Sum(F('selling_price') * F('quantity'))
        )['total'] or 0

        total_income = total_projects_income + total_shop_income

        # Expenses Breakdown
        salary_costs = SalaryWorkers.objects.filter(is_still_active=True).aggregate(total=Sum('salary'))['total'] or 0
        contractor_costs = ProductContractor.objects.aggregate(total=Sum('cost'))['total'] or 0
        raw_material_costs = AddRawMaterials.objects.aggregate(
            total=Sum(F('item__price') * F('quantity'))
        )['total'] or 0
        asset_costs = Assets.objects.aggregate(total=Sum('value'))['total'] or 0
        other_expenses = Expense.objects.aggregate(total=Sum('amount'))['total'] or 0

        total_expenses = sum([salary_costs, contractor_costs, raw_material_costs, asset_costs, other_expenses])

        # Profit Calculations
        net_profit = total_income - total_expenses
        gross_profit = (total_projects_income + total_shop_income) - (
                    raw_material_costs + salary_costs + contractor_costs)

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

        # Inventory Value
        inventory_value = InventoryItem.objects.aggregate(
            total=Sum(F('stock') * F('selling_price'))
        )['total'] or 0

        # Monthly Trends
        monthly_income = get_monthly_data(
            Sold, 'date', F('selling_price') * F('quantity')
        )

        monthly_expenses = []
        for i in range(12):
            month_start = today.replace(day=1) - timedelta(days=30 * i)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            expenses = {
                'salary': SalaryWorkers.objects.filter(
                    is_still_active=True,
                    created_at__lte=month_end
                ).aggregate(total=Sum('salary'))['total'] or 0,
                'contractors': ProductContractor.objects.filter(
                    product__project__start_date__gte=month_start,
                    product__project__start_date__lte=month_end
                ).aggregate(total=Sum('cost'))['total'] or 0,
                'materials': AddRawMaterials.objects.filter(
                    date__gte=month_start,
                    date__lte=month_end
                ).aggregate(total=Sum(F('item__price') * F('quantity')))['total'] or 0,
                'other': Expense.objects.filter(
                    date__gte=month_start,
                    date__lte=month_end
                ).aggregate(total=Sum('amount'))['total'] or 0
            }

            monthly_expenses.append({
                'month': month_start.strftime("%b %Y"),
                'total': sum(expenses.values()),
                'breakdown': expenses
            })

        monthly_expenses.reverse()

        # Categorical Breakdowns
        expense_categories = ExpenseCategory.objects.annotate(
            total=Sum('expense__amount')
        ).values('name', 'total').order_by('-total')

        # Asset Analysis
        asset_analysis = Assets.objects.aggregate(
            active=Sum('value', filter=Q(is_still_available=True)),
            deprecated=Sum('value', filter=Q(is_still_available=False))
        )

        data = {
            'key_metrics': {
                'total_income': round(total_income, 2),
                'total_expenses': round(total_expenses, 2),
                'net_profit': round(net_profit, 2),
                'gross_profit': round(gross_profit, 2),
                'current_assets_value': round(asset_analysis.get('active', 0), 2),
                'inventory_value': round(inventory_value, 2)
            },
            'income_breakdown': {
                'projects': round(total_projects_income, 2),
                'shop_sales': round(total_shop_income, 2),
                'percentage_projects': round((total_projects_income / total_income * 100) if total_income else 0, 2),
                'percentage_shop': round((total_shop_income / total_income * 100) if total_income else 0, 2)
            },
            'expense_breakdown': {
                'salaries': round(salary_costs, 2),
                'contractors': round(contractor_costs, 2),
                'raw_materials': round(raw_material_costs, 2),
                'assets': round(asset_costs, 2),
                'other_expenses': round(other_expenses, 2),
                'operational_ratio': round((total_expenses / total_income * 100) if total_income else 0, 2)
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
            'categorical_data': {
                'expense_categories': [
                    {'name': cat['name'], 'value': cat['total']}
                    for cat in expense_categories if cat['total']
                ],
                'project_profitability': list(project_profitability),
                'asset_analysis': {
                    'active_assets': asset_analysis.get('active', 0),
                    'deprecated_assets': asset_analysis.get('deprecated', 0)
                }
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