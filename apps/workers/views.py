from django.db import transaction
from rest_framework.filters import SearchFilter
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.db.models.functions import Round, Coalesce
from django.db.models import IntegerField
from django.shortcuts import get_object_or_404
from rest_framework import status
from datetime import date

from .models import (
    Contractors, SalaryWorkers, ContractorRecord, SalaryWorkersRecord, Paid
)
from .serializers import (
    ContractorsSerializer, SalaryWorkersSerializer, ContractorRecordSerializer,
    SalaryWorkersRecordSerializer, PaidSerializer
)
from .filters import PaidFilter
from api.permissions import CheckUserRoles
from api.utils import swagger_helper
from rest_framework.decorators import action
from django.utils import timezone


class ApiContractors(ModelViewSet):
    serializer_class = ContractorsSerializer
    queryset = Contractors.objects.all()
    permission_classes = [CheckUserRoles]
    required_roles = ['factory_manager', 'project_manager', 'admin', 'ceo', 'accountant']
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_still_active']
    search_fields = ['first_name', 'last_name', 'email']


    @swagger_helper("Contractors", "Contractor")
    def list(self, request, *args, **kwargs):
        try:
            today = timezone.now().date()
            start_of_week = today - timezone.timedelta(days=today.weekday())

            filtered_contractors = self.filter_queryset(self.get_queryset())

            all_contractors_count = filtered_contractors.count()
            all_active_contractors_count = filtered_contractors.filter(is_still_active=True).count()
            total_contractors_monthly_pay = filtered_contractors.filter(
                paid__date__month=today.month
            ).aggregate(total=Sum("paid__amount"))["total"] or 0.0
            total_contractors_weekly_pay = filtered_contractors.filter(
                paid__date__range=(start_of_week, today)
            ).aggregate(total=Sum("paid__amount"))["total"] or 0.0

            page = self.paginate_queryset(filtered_contractors)
            if page is not None:
                data = self.serializer_class(page, many=True, context={'request': request}).data
                response_data = {
                    "all_contractors_count": all_contractors_count,
                    "all_active_contractors_count": all_active_contractors_count,
                    "total_contractors_monthly_pay": float(total_contractors_monthly_pay),
                    "total_contractors_weekly_pay": float(total_contractors_weekly_pay),
                    "contractor": data,
                }
                return self.get_paginated_response(response_data)

            data = self.serializer_class(filtered_contractors, many=True, context={'request': request}).data
            response_data = {
                "all_contractors_count": all_contractors_count,
                "all_active_contractors_count": all_active_contractors_count,
                "total_contractors_monthly_pay": float(total_contractors_monthly_pay),
                "total_contractors_weekly_pay": float(total_contractors_weekly_pay),
                "contractor": data,
            }

            return Response(response_data)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


    @swagger_helper("Contractors", "Contractor")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_helper("Contractors", "Contractor")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Contractors", "Contractor")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_helper("Contractors", "Contractor")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_helper("Contractors", "Contractor")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class ApiSalaryWorkers(ModelViewSet):
    serializer_class = SalaryWorkersSerializer
    queryset = SalaryWorkers.objects.all()
    permission_classes = [CheckUserRoles]
    required_roles = ['admin', 'factory_manager', 'ceo', "project_manager", 'accountant']
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_still_active']
    search_fields = ['first_name', 'last_name', 'email']


    @swagger_helper("Salary Workers", "Salary Worker")
    def list(self, request, *args, **kwargs):
        try:
            today = timezone.now().date()
            start_of_week = today - timezone.timedelta(days=today.weekday())

            filtered_salary_workers = self.filter_queryset(self.get_queryset())

            salary_workers_count = filtered_salary_workers.count()
            active_salary_workers_count = filtered_salary_workers.filter(is_still_active=True).count()
            total_salary_workers_monthly_pay = filtered_salary_workers.filter(is_still_active=True).aggregate(total=Sum("salary"))["total"] or 0.0
            total_paid = filtered_salary_workers.filter(paid__date__month=today.month).aggregate(total=Sum("paid__amount"))["total"] or 0.0

            page = self.paginate_queryset(filtered_salary_workers)
            if page is not None:
                data = self.serializer_class(page, many=True, context={'request': request}).data
                response_data = {
                    "salary_workers_count": salary_workers_count,
                    "active_salary_workers_count": active_salary_workers_count,
                    "total_salary_workers_monthly_pay": float(total_salary_workers_monthly_pay),
                    "total_paid": float(total_paid),
                    "workers": data,
                }
                return self.get_paginated_response(response_data)

            data = self.serializer_class(filtered_salary_workers, many=True, context={'request': request}).data
            response_data = {
                "salary_workers_count": salary_workers_count,
                "active_salary_workers_count": active_salary_workers_count,
                "total_salary_workers_monthly_pay": float(total_salary_workers_monthly_pay),
                "total_paid": float(total_paid),
                "workers": data,
            }

            return Response(response_data)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


    @swagger_helper("Salary Workers", "Salary Worker")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_helper("Salary Workers", "Salary Worker")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Salary Workers", "Salary Worker")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_helper("Salary Workers", "Salary Worker")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_helper("Salary Workers", "Salary Worker")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class ContractorDetailViewSet(ViewSet):
    permission_classes = [CheckUserRoles]
    required_roles = ['factory_manager', 'project_manager', 'admin', 'ceo', 'accountant']

    @swagger_helper("Contractor Details", "Contractor Detail")
    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        try:
            contractor = Contractors.objects.get(id=pk)
            products_paginator = StandardResultsSetPagination()
            payments_paginator = StandardResultsSetPagination()
            products_paginator.page_query_param = 'products_page'
            payments_paginator.page_query_param = 'payments_page'
            product_contractors = ProductContractor.objects.filter(contractor=contractor).order_by("-date", "-id")
            products_page = products_paginator.paginate_queryset(product_contractors, request, view=self)
            products_data = [
                {
                    'id': pc.id,
                    'product': {
                        'id': pc.product.id,
                        'name': pc.product.name,
                        'project': pc.product.project.id if pc.product.project else None,
                        'selling_price': float(pc.product.selling_price),
                        'progress': pc.product.progress
                    },
                    'cost': float(pc.cost),
                    'date': pc.date.isoformat()
                } for pc in products_page
            ]
            payments = Paid.objects.filter(contract=contractor).order_by("-date", "-id")
            payments_page = payments_paginator.paginate_queryset(payments, request, view=self)
            payments_data = [
                {
                    'id': p.id,
                    'amount': float(p.amount),
                    'date': p.date.isoformat()
                } for p in payments_page
            ]
            response_data = {
                'id': contractor.id,
                'first_name': contractor.first_name,
                'last_name': contractor.last_name,
                'email': contractor.email,
                'products': {
                    'results': products_data,
                    'count': products_paginator.page.paginator.count,
                    'next': products_paginator.get_next_link(),
                    'previous': products_paginator.get_previous_link()
                },
                'payments': {
                    'results': payments_data,
                    'count': payments_paginator.page.paginator.count,
                    'next': payments_paginator.get_next_link(),
                    'previous': payments_paginator.get_previous_link()
                }
            }
            return JsonResponse(response_data, status=200)
        except Contractors.DoesNotExist:
            return JsonResponse({"error": "Contractor not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


class SalaryWorkerDetailViewSet(ViewSet):
    permission_classes = [CheckUserRoles]
    required_roles = ['admin', 'factory_manager', 'ceo', 'project_manager', 'accountant']

    @swagger_helper("Salary Worker Details", "Salary Worker Detail")
    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        try:
            salary_worker = SalaryWorkers.objects.get(id=pk)
            products_paginator = StandardResultsSetPagination()
            payments_paginator = StandardResultsSetPagination()
            products_paginator.page_query_param = 'products_page'
            payments_paginator.page_query_param = 'payments_page'
            product_salary_workers = ProductSalaryWorker.objects.filter(salary_worker=salary_worker).order_by("-date", "-id")
            products_page = products_paginator.paginate_queryset(product_salary_workers, request, view=self)
            products_data = [
                {
                    'id': psw.id,
                    'product': {
                        'id': psw.product.id,
                        'name': psw.product.name,
                        'project': psw.product.project.id if psw.product.project else None,
                        'selling_price': float(psw.product.selling_price),
                        'progress': psw.product.progress
                    },
                    'date': psw.date.isoformat()
                } for psw in products_page
            ]
            payments = Paid.objects.filter(salary=salary_worker).order_by("-date", "-id")
            payments_page = payments_paginator.paginate_queryset(payments, request, view=self)
            payments_data = [
                {
                    'id': p.id,
                    'amount': float(p.amount),
                    'date': p.date.isoformat()
                } for p in payments_page
            ]
            response_data = {
                'id': salary_worker.id,
                'first_name': salary_worker.first_name,
                'last_name': salary_worker.last_name,
                'email': salary_worker.email,
                'products': {
                    'results': products_data,
                    'count': products_paginator.page.paginator.count,
                    'next': products_paginator.get_next_link(),
                    'previous': products_paginator.get_previous_link()
                },
                'payments': {
                    'results': payments_data,
                    'count': payments_paginator.page.paginator.count,
                    'next': payments_paginator.get_next_link(),
                    'previous': payments_paginator.get_previous_link()
                }
            }
            return JsonResponse(response_data, status=200)
        except SalaryWorkers.DoesNotExist:
            return JsonResponse({"error": "Salary Worker not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)



class ApiSalaryWorkersRecord(ModelViewSet):
    serializer_class = SalaryWorkersRecordSerializer
    permission_classes = [CheckUserRoles]
    required_roles = ['admin', 'factory_manager', 'ceo', 'accountant']

    def get_queryset(self):
        salary_id = self.kwargs.get('salary_worker_pk')
        return SalaryWorkersRecord.objects.filter(salary_worker=salary_id)

    @swagger_helper("Salary Worker Records", "Salary Worker Record")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_helper("Salary Worker Records", "Salary Worker Record")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_helper("Salary Worker Records", "Salary Worker Record")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Salary Worker Records", "Salary Worker Record")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_helper("Salary Worker Records", "Salary Worker Record")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_helper("Salary Worker Records", "Salary Worker Record")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        salary_id = self.kwargs.get('salary_worker_pk')
        salary_worker = get_object_or_404(SalaryWorkers, pk=salary_id)
        serializer.save(salary_worker=salary_worker)

    def perform_update(self, serializer):
        salary_id = self.kwargs.get('salary_worker_pk')
        salary_worker = get_object_or_404(SalaryWorkers, pk=salary_id)
        serializer.save(salary_worker=salary_worker)


class ApiContractorRecord(ModelViewSet):
    serializer_class = ContractorRecordSerializer
    permission_classes = [CheckUserRoles]
    required_roles = ['admin', 'factory_manager', 'ceo', 'accountant']

    def get_queryset(self):
        contractor_id = self.kwargs.get('contractor_pk')
        return ContractorRecord.objects.filter(contractor=contractor_id)

    def perform_create(self, serializer):
        contractor_id = self.kwargs.get('contractor_pk')
        contractor = get_object_or_404(Contractors, pk=contractor_id)
        serializer.save(contractor=contractor)

    def perform_update(self, serializer):
        contractor_id = self.kwargs.get('contractor_pk')
        contractor = get_object_or_404(Contractors, pk=contractor_id)
        serializer.save(contractor=contractor)

    @swagger_helper("Contractor Records", "Contractor Record")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_helper("Contractor Records", "Contractor Record")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_helper("Contractor Records", "Contractor Record")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Contractor Records", "Contractor Record")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_helper("Contractor Records", "Contractor Record")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_helper("Contractor Records", "Contractor Record")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class ApiPaid(ModelViewSet):
    serializer_class = PaidSerializer
    queryset = Paid.objects.all().order_by('-date')
    filterset_class = PaidFilter
    permission_classes = [CheckUserRoles]
    required_roles = ['factory_manager', 'admin', 'ceo', 'accountant']

    @swagger_helper("Paid Records", "Paid Record")
    def list(self, request, *args, **kwargs):
        today = timezone.now().date()
        queryset = self.get_queryset()
        filterset = self.filterset_class(request.GET, queryset=self.get_queryset())
        filtered_paid = filterset.qs.order_by('-date')

        monthly_total = filtered_paid.filter(date__month=today.month).aggregate(total=Sum('amount'))['total'] or 0.0
        salary_paid_this_month = filtered_paid.filter(date__month=today.month, contract=None).aggregate(Sum('amount'))['amount__sum'] or 0.0
        contractors_paid_this_month = filtered_paid.filter(date__month=today.month, salary=None).aggregate(Sum('amount'))['amount__sum'] or 0.0
        # filters
        year = request.query_params.get('year', None)
        month = request.query_params.get('month', None)
        day = request.query_params.get('day', None)

        filtered = filtered_paid

        if day is not None and year is None and month is None:
            year = today.year
            month = today.month

        if year is None and month is None:
            year = today.year
            month = today.month

        if year is not None and month is None and day is None:
            filtered = filtered_paid.filter(date__year=year)

        elif year is not None and day is not None:
            if month is None:
                month = today.month
            filtered = filtered_paid.filter(date__year=year, date__month=month, date__day=day)

        elif year is not None and month is not None and day is None:
            filtered = filtered_paid.filter(date__year=year, date__month=month)

        elif year is not None and month is not None and day is not None:
            filtered = filtered_paid.filter(date__year=year, date__month=month, date__day=day)

        daily_data = []
        current_date = None
        daily_paid = []
        for paid in filtered:
            paid_date = paid.date.date() if isinstance(paid.date, datetime) else paid.date

            if current_date != paid_date:
                if daily_paid:
                    daily_data.append({
                        "date": current_date,
                        "entries": self.get_serializer(daily_paid, many=True).data,
                        "daily_total": sum(s.amount for s in daily_paid)
                    })
                current_date = paid_date
                daily_paid = [paid]
            else:
                daily_paid.append(paid)
        if daily_paid:
            daily_data.append({
                "date": current_date,
                "entries": self.get_serializer(daily_paid, many=True).data,
                "daily_total": sum(s.amount for s in daily_paid)
            })
        response_data = {
            "monthly_total": monthly_total,
            "salary_paid_this_month": salary_paid_this_month,
            "contractors_paid_this_month": contractors_paid_this_month,
            "daily_data": daily_data,
        }
        if year:
            yearly_total = queryset.filter(date__year=year).aggregate(total=Sum("amount"))['total'] or 0.0
            response_data["yearly_total"] = yearly_total
        return Response(response_data)


    @swagger_helper("Paid Records", "Paid Record")
    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            if request.data.get('contractor'):
                contractor = get_object_or_404(Contractors, pk=request.data.get('contractor'))
                if 'amount' in request.data:
                    amount = float(request.data.get('amount'))
                    serializer.save(contractor=contractor)
                    if contractor.monthly_pay.count() > 0:
                        contractor.monthly_pay.create(
                            date=date.today(),
                            amount=amount,
                            description=request.data.get('description', '')
                        )
            elif request.data.get('salary_worker'):
                salary_worker = get_object_or_404(SalaryWorkers, pk=request.data.get('salary_worker'))
                if 'amount' in request.data:
                    amount = float(request.data.get('amount'))
                    serializer.save(salary_worker=salary_worker)
                    if salary_worker.monthly_pay.count() > 0:
                        salary_worker.monthly_pay.create(
                            date=date.today(),
                            amount=amount,
                            description=request.data.get('description', '')
                        )
            else:
                return Response({'error': 'Please provide either contractor or salary_worker'},
                             status=status.HTTP_400_BAD_REQUEST)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @swagger_helper("Paid Records", "Paid Record")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Paid Records", "Paid Record")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_helper("Paid Records", "Paid Record")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_helper("Paid Records", "Paid Record")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
