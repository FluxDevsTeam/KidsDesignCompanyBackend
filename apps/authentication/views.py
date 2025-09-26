from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.mail import send_mail
import random
from rest_framework import viewsets, status
from django.contrib.auth.hashers import make_password
from rest_framework.filters import SearchFilter
from .serializers import (UserSignupSerializer, LoginSerializer, GroupSerializer)
from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework.response import Response
from django.utils.timezone import now
from django.contrib.auth.models import Group
from .permissions import IsCeo

User = get_user_model()


class GroupViewSet(viewsets.ModelViewSet):
    """Only the CEO is allowed to create a new role, endpoint to CRUD Group(roles)
    ['storekeeper', 'shopkeeper', 'factory_manager', 'product_manager', 'admin', 'accountant' 'ceo']"""

    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsCeo]
    filter_backends = [SearchFilter]
    search_fields = ["name"]


class UserSignupViewSet(viewsets.ModelViewSet):
    """
    ModelViewSet for handling user signup and OTP verification.
    example of object for creating new user:
    {
        "first_name": "",
        "last_name": "",
        "email": "",
        "password": "",
        "verify_password": "",
        "phone_number": "",
        "roles": ["shopkeeper"]
    }
    """
    queryset = User.objects.all().order_by("-id")
    serializer_class = UserSignupSerializer
    permission_classes = [IsCeo]

    def create(self, request, *args, **kwargs):
        """
        Handles user signup.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        phone_number = serializer.validated_data['phone_number']
        roles = serializer.validated_data.pop('groups', [])

        # Check if the user already exists
        user = User.objects.filter(email=email).first()

        if user:
            if not user.is_verified:
                otp = random.randint(100000, 999999)
                user.otp = otp
                user.otp_created_at = now()
                user.save()

                send_mail(
                    subject='Verify your email',
                    message=f'Your OTP is: {otp}',
                    recipient_list=[email],
                    from_email=settings.EMAIL_HOST_USER,
                )

                return Response(
                    {"message": "User already exists but is not verified. OTP resent."},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": "User already exists and is verified."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Create new user
        user = User.objects.create(
            first_name=serializer.validated_data['first_name'],
            last_name=serializer.validated_data['last_name'],
            email=email,
            password=make_password(password),
            phone_number=phone_number,
            is_verified=True
        )
        user.groups.set(roles)
        return Response({
            'message': 'Signup successful.',
        }, status=status.HTTP_200_OK)


class UserLoginViewSet(viewsets.ViewSet):
    """
    Handles user login and token generation.
    """

    serializer_class = LoginSerializer

    def create(self, request, *args, **kwargs):
        if request.method != 'POST':
            return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

        data = request.data
        email = data.get('email')
        password = data.get('password')

        # Check if user exists
        user = User.objects.filter(email=email).first()
        if not user:
            return Response({'message': 'User does not exist'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.is_verified:
            return Response({'message': 'Please verify your email first'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(password):
            return Response({'message': 'Invalid password'}, status=status.HTTP_400_BAD_REQUEST)

        # Generate tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        try:
            group = user.groups.first()
            group_name = group.name if group else None
        except Group.DoesNotExist:
            group_name = None

        return Response({
            'message': 'Login successful.',
            'access_token': access_token,
            'refresh_token': str(refresh),
            'role': group_name
        }, status=status.HTTP_200_OK)
