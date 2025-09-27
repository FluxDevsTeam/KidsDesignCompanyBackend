from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="KidsDesignCompanyBackend",
        default_version='v1',
        description="""
            An API for Kids Design Company backend.

            **Servers:**
            - Local: [http://localhost:8000](http://localhost:8000)
            - Production: [https://kidsdesigncompany.pythonanywhere.com/](https://kidsdesigncompany.pythonanywhere.com/)
            """,    
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="suskidee@gmail.com"),
        license=openapi.License(name="Test License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

