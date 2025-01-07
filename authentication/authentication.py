# yourapp/authentication.py
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model


class EmailAuthentication(BaseAuthentication):
    def authenticate(self, request):
        email = request.data.get('email', None)
        password = request.data.get('password', None)

        if not email or not password:
            return None

        User = get_user_model()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise AuthenticationFailed('No user found with this email.')

        if not user.check_password(password):
            raise AuthenticationFailed('Invalid password.')

        return (user, None)
