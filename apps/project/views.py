from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework import mixins
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F, Sum, ExpressionWrapper, DecimalField
from django.db.models.functions import Round, Coalesce, Cast
from django.db.models import IntegerField

from .models import Project, OverheadCost, OtherProduction
from .serializers import ProjectSerializer, OtherProductionSerializer, OverheadCostSerializer
from .filters import ProjectFilter
from api.permissions import CheckUserRoles
from api.utils import swagger_helper
from django.db.models import Avg, IntegerField
from django.utils import timezone
from rest_framework.response import Response


class ApiProject(ModelViewSet):
    serializer_class = ProjectSerializer
    queryset = Project.objects.all().order_by("start_date")
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProjectFilter
    search_fields = ['customer__name', 'name']
    ordering = ['start_date', "deadline"]
    permission_classes = [CheckUserRoles]
    required_roles = ['factory_manager', 'project_manager', 'ceo', 'shopkeeper', 'admin', 'accountant']

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.annotate(computed_progress=Cast(Round(Avg('product__progress')), output_field=IntegerField()))
        return qs
    
    @swagger_helper("Project", "Project")
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        get_all = self.get_queryset()
        all_time_projects_count = get_all.count()
        all_projects_count = get_all.filter(is_delivered=False, archived=False).count()
        overdue_projects_count =get_all.filter(is_delivered=False, archived=False, deadline__lt=timezone.now().date()).count()
        ongoing_projects_count = get_all.filter(computed_progress__lt=100).count()
        average_progress = get_all.filter(is_delivered=False, archived=False).aggregate(avg_progress=Avg("computed_progress"))["avg_progress"] or 0

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_data = {
                "count": self.paginator.page.paginator.count,
                "next": self.paginator.get_next_link(),
                "previous": self.paginator.get_previous_link(),
                "all_time_projects_count": all_time_projects_count,
                "all_projects_count": all_projects_count,
                "overdue_projects_count": overdue_projects_count,
                "ongoing_projects_count": ongoing_projects_count,
                "average_progress": round(average_progress, 2),
                "all_projects": serializer.data,
            }
            return Response(response_data)

        serializer = self.get_serializer(queryset, many=True)
        response_data = {
            "count": queryset.count(),
            "next": None,
            "previous": None,
            "all_time_projects_count": all_time_projects_count,
            "all_ongoing_projects_count": all_projects_count,
            "overdue_projects_count": overdue_projects_count,
            "ongoing_projects_count": ongoing_projects_count,
            "average_progress": round(average_progress, 2),
            "all_projects": serializer.data,
        }
        return Response(response_data)

    @swagger_helper("Project", "Project")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_helper("Project", "Project")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Project", "Project")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_helper("Project", "Project")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_helper("Project", "Project")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class ApiOtherProductionRecord(ModelViewSet):
    serializer_class = OtherProductionSerializer
    permission_classes = [CheckUserRoles]
    required_roles = ['factory_manager', 'project_manager', 'ceo']

    def get_queryset(self):
        project_id = self.kwargs.get('project_pk')
        return OtherProduction.objects.filter(project=project_id)

    def perform_create(self, serializer):
        project_id = self.kwargs.get('project_pk')
        project = get_object_or_404(Project, pk=project_id)
        serializer.save(project=project)

    def perform_update(self, serializer):
        project_id = self.kwargs.get('project_pk')
        project = get_object_or_404(Project, pk=project_id)
        serializer.save(project=project)

    @swagger_helper("Project", "Other Production Record")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_helper("Other Production Record", "Other Production Record")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_helper("Other Production Record", "Other Production Record")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Other Production Record", "Other Production Record")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_helper("Other Production Record", "Other Production Record")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_helper("Other Production Record", "Other Production Record")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class OverheadCostViewSet(mixins.UpdateModelMixin, GenericViewSet):
    serializer_class = OverheadCostSerializer
    permission_classes = [CheckUserRoles]
    required_roles = ['ceo']


    def get_queryset(self):
        return OverheadCost.objects.all()

    def get_object(self):
        instance, created = OverheadCost.objects.get_or_create(id=1)
        return instance

    @swagger_helper("Overhead Cost", "Overhead Cost")
    def list(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


    @swagger_helper("Overhead Cost", "Overhead Cost")
    def update(self, request, *args, **kwargs):
        if request.method.upper() == 'PUT':
            return Response(
                {'detail': 'PUT method is not allowed; only PATCH is permitted.'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        return super().update(request, *args, **kwargs)


    @swagger_helper("Overhead Cost", "Overhead Cost")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)