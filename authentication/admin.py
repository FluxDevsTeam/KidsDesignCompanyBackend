from django.contrib import admin
from .models import NameChangeRequest, EmailChangeRequest, ForgotPasswordRequest, PasswordChangeRequest, User
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin

admin.site.register(NameChangeRequest)
admin.site.register(EmailChangeRequest)
admin.site.register(ForgotPasswordRequest)
admin.site.register(PasswordChangeRequest)


# custom user

@admin.register(User)
class UserAdmin(DefaultUserAdmin):
    # Fields to display in the user list view
    list_display = ('email', 'is_staff', 'is_active', 'is_verified', 'phone_number')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_verified')
    search_fields = ('email', 'phone_number')
    ordering = ('email',)

    # Fieldsets for viewing and editing a user
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Information', {'fields': ('phone_number',)}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions')
        }),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    # Fieldsets for adding a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active', 'is_verified')}
         ),
    )
