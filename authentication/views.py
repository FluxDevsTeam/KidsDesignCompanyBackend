from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.mail import send_mail
import random
import datetime
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from django.contrib.auth.hashers import make_password
from rest_framework.exceptions import AuthenticationFailed
from .serializers import (UserSignupSerializer, LoginSerializer, PasswordChangeRequestSerializer, \
                          UserProfileSerializer, ForgotPasswordRequestSerializer, UserSignupSerializerResendOTP,
                          UserSignupSerializerOTP, ViewUserProfileSerializer)
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from .utils import EmailThread
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import EmailChangeRequest, PasswordChangeRequest, ForgotPasswordRequest, NameChangeRequest
from django.utils.timezone import now

User = get_user_model()


class ForgotPasswordViewSet(viewsets.ModelViewSet):
    queryset = ForgotPasswordRequest.objects.all()
    serializer_class = ForgotPasswordRequestSerializer

    @action(detail=False, methods=['post'], url_path='request-forgot-password')
    def request_forgot_password(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "No user found with this email."}, status=status.HTTP_400_BAD_REQUEST)

        reset_url = f"https://asluxeryoriginals.pythonanywhere.com/auth/forgot-password/set-new-password/?email={email}"
        ForgotPasswordRequest.objects.create(user=user)
        send_mail(
            subject='Password Reset Request',
            message=f"Click the following link to reset your password: {reset_url}. This link will expire in 10 minutes.",
            recipient_list=[email],
            from_email=settings.EMAIL_HOST_USER,
        )

        return Response({"message": "A password reset link has been sent to your email."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='set-new-password')
    def set_new_password(self, request):
        email = request.data.get('email')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not email or not new_password or not confirm_password:
            return Response({"error": "Email, new_password, and confirm_password are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({"error": "Password must be at least 8 characters long."},
                            status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({"error": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "No user found with this email."}, status=status.HTTP_400_BAD_REQUEST)
        forgot_password_request = ForgotPasswordRequest.objects.filter(user=user).first()
        expiration_time = forgot_password_request.created_at + datetime.timedelta(minutes=10)
        if timezone.now() > expiration_time:
            return Response({"error": "The reset link has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)

        ForgotPasswordRequest.objects.filter(user=user).delete()
        otp = random.randint(100000, 999999)

        send_mail(
            subject='Forgot Password OTP',
            message=f"Your OTP for password reset is: {otp}. It will expire in 5 minutes.",
            recipient_list=[email],
            from_email=settings.EMAIL_HOST_USER,
        )

        ForgotPasswordRequest.objects.create(user=user, otp=otp, new_password=new_password)

        return Response({"message": "An OTP has been sent to your email."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='verify-otp')
    def verify_otp(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')

        if not email or not otp:
            return Response({"error": "Email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "No user found with this email."}, status=status.HTTP_400_BAD_REQUEST)

        forgot_password_request = ForgotPasswordRequest.objects.filter(user=user).first()
        if not forgot_password_request:
            return Response({"error": "No pending forgot password request found."}, status=status.HTTP_400_BAD_REQUEST)

        if str(forgot_password_request.otp) != str(otp):
            return Response({"error": "Incorrect OTP."}, status=status.HTTP_400_BAD_REQUEST)

        otp_age = (timezone.now() - forgot_password_request.created_at).total_seconds()
        if otp_age > 300:
            return Response({"error": "OTP has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)

        user.password = make_password(forgot_password_request.new_password)
        if not user.is_verified:
            user.is_verified = True
        user.save()

        forgot_password_request.delete()

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        return Response({
            'message': 'Password reset successful.',
            'access_token': access_token,
            'refresh_token': str(refresh),
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='resend-otp')
    def resend_otp(self, request):
        email = request.data.get('email')

        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "No user found with this email."}, status=status.HTTP_400_BAD_REQUEST)

        forgot_password_request = ForgotPasswordRequest.objects.filter(user=user).first()
        if not forgot_password_request:
            return Response({"error": "No pending forgot password request found."}, status=status.HTTP_400_BAD_REQUEST)

        # Generate a new OTP
        otp = random.randint(100000, 999999)
        forgot_password_request.otp = otp

        # Extend the expiration time by 5 minutes from now
        forgot_password_request.created_at = timezone.now()  # Reset the creation time to current time

        # Save the updated OTP and expiration time
        forgot_password_request.save()

        # Send the new OTP to the user
        send_mail(
            subject='Forgot Password OTP - Resent',
            message=f"Your new OTP for password reset is: {otp}. It will expire in 5 minutes.",
            recipient_list=[email],
            from_email=settings.EMAIL_HOST_USER,
        )

        return Response({"message": "A new OTP has been sent to your email and the expiration time has been extended."}, status=status.HTTP_200_OK)


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for retrieving and updating the user's profile.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        """
        Returns the profile of the currently authenticated user along with their orders.
        """
        user = request.user
        serializer = ViewUserProfileSerializer(user, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='request-email-change')
    def request_email_change(self, request):
        """
        Request email change with OTP sent to the new email.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        new_email = serializer.validated_data.get('new_email')
        password = serializer.validated_data.get('password')

        if not user.check_password(password):
            return Response({"error": "Incorrect password."}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=new_email).exists():
            return Response({"error": "This email is already in use."}, status=status.HTTP_400_BAD_REQUEST)

        # Optional: Check if there is an existing pending request and reuse it
        existing_request = EmailChangeRequest.objects.filter(user=user).first()
        if existing_request:
            otp = random.randint(100000, 999999)
            existing_request.new_email = new_email
            existing_request.otp = otp
            existing_request.created_at = timezone.now()
            existing_request.save()
        else:
            otp = random.randint(100000, 999999)
            EmailChangeRequest.objects.create(user=user, new_email=new_email, otp=otp)

        send_mail(
            subject='Email Change OTP',
            message=f"Your OTP is: {otp}",
            recipient_list=[new_email],
            from_email=settings.EMAIL_HOST_USER,
        )

        return Response({"message": "OTP sent to the new email address."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='resend-email-change-otp')
    def resend_email_change_otp(self, request):
        """
        Resend OTP for email change.
        """
        user = request.user
        email_change_request = EmailChangeRequest.objects.filter(user=user).first()

        if not email_change_request:
            return Response({"error": "No pending email change request found."}, status=status.HTTP_400_BAD_REQUEST)

        # Rate limiting: Allow resending OTP only after 1 minute
        time_since_last_otp = (timezone.now() - email_change_request.created_at).total_seconds()
        if time_since_last_otp < 60:
            return Response({"error": "Please wait before requesting a new OTP."}, status=status.HTTP_400_BAD_REQUEST)

        otp = random.randint(100000, 999999)
        email_change_request.otp = otp
        email_change_request.created_at = timezone.now()
        email_change_request.save()

        send_mail(
            subject='Resend Email Change OTP',
            message=f"Your new OTP is: {otp}",
            recipient_list=[email_change_request.new_email],
            from_email=settings.EMAIL_HOST_USER,
        )

        return Response({"message": "New OTP sent to the new email address."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='verify-email-change')
    def verify_email_change(self, request):
        """
        Verify OTP and update the user's email.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        otp = serializer.validated_data.get('otp')

        email_change_request = EmailChangeRequest.objects.filter(user=user).first()
        if not email_change_request:
            return Response({"error": "No pending email change request found."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if OTP matches
        if str(email_change_request.otp) != str(otp):
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if OTP has expired (5 minutes validity)
        otp_age = (timezone.now() - email_change_request.created_at).total_seconds()
        if otp_age > 300:
            return Response({"error": "OTP has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)

        user.email = email_change_request.new_email
        user.save()
        email_change_request.delete()

        # Send confirmation email
        send_mail(
            subject='Email Change Confirmation',
            message="Your email address has been successfully changed.",
            recipient_list=[user.email],
            from_email=settings.EMAIL_HOST_USER,
        )

        return Response({"message": "Email updated successfully."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='request-profile-change')
    def request_profile_change(self, request):
        """
        Request name change , just submitting the request with new name details.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        new_first_name = serializer.validated_data.get('new_first_name')
        new_last_name = serializer.validated_data.get('new_last_name')
        new_phone_number = serializer.validated_data.get('new_phone_number')

        if not new_first_name and not new_last_name and not new_phone_number:
            return Response({"error": "At least one of new_first_name or new_last_name or new_phone_number is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Clear any existing pending name change requests
        NameChangeRequest.objects.filter(user=user).delete()

        # Create a new name change request
        NameChangeRequest.objects.create(
            user=user,
            new_first_name=new_first_name,
            new_last_name=new_last_name,
            new_phone_number=new_phone_number,
        )

        return Response({"message": "Name change request submitted successfully."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='verify-profile-change')
    def verify_profile_change(self, request):
        """
        Verify password and update the user's name.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        password = serializer.validated_data.get('password')

        # Verify the password provided by the user
        if not user.check_password(password):
            return Response({"error": "Incorrect password."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the latest name change request
        name_change_request = NameChangeRequest.objects.filter(user=user).first()
        if not name_change_request:
            return Response({"error": "No pending name change request found."}, status=status.HTTP_400_BAD_REQUEST)

        # Update the user's name if the request exists
        if name_change_request.new_first_name:
            user.first_name = name_change_request.new_first_name
        if name_change_request.new_last_name:
            user.last_name = name_change_request.new_last_name
        if name_change_request.new_phone_number:
            user.phone_number = name_change_request.new_phone_number

        user.save()
        name_change_request.delete()

        send_mail(
            subject='Profile Change Confirmation',
            message="Your profile has been successfully updated.",
            recipient_list=[user.email],
            from_email=settings.EMAIL_HOST_USER,
        )

        return Response({"message": "Name updated successfully."}, status=status.HTTP_200_OK)


class PasswordChangeRequestViewSet(viewsets.ModelViewSet):
    """
    Handles password change requests with OTP verification.
    """
    permission_classes = [IsAuthenticated]
    queryset = PasswordChangeRequest.objects.all()
    serializer_class = PasswordChangeRequestSerializer

    @action(detail=False, methods=['post'], url_path='request-password-change')
    def request_password_change(self, request):
        """
        Request a password change with OTP verification sent to email.
        """
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        # Check if old password is provided and matches
        if not old_password:
            return Response({"error": "Old password is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(old_password):
            return Response({"error": "Old password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure old and new passwords are not the same
        if old_password == new_password:
            return Response({"error": "New password cannot be the same as the old password."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Validate new password and confirmation
        if not new_password or not confirm_password:
            return Response({"error": "Both new_password and confirm_password are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({"error": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({"error": "Password must be at least 8 characters long."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Clear previous requests and create a new one
        PasswordChangeRequest.objects.filter(user=user).delete()
        otp = random.randint(100000, 999999)

        send_mail(
            subject='Password Change OTP',
            message=f"Your OTP for password change is: {otp}",
            recipient_list=[user.email],
            from_email=settings.EMAIL_HOST_USER,
        )
        PasswordChangeRequest.objects.create(user=user, otp=otp, new_password=new_password)

        return Response({"message": "An OTP has been sent to your email."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='resend-otp')
    def resend_otp(self, request):
        """
        Request a new OTP if the previous one has expired or was invalid.
        """
        user = request.user

        password_change_request = PasswordChangeRequest.objects.filter(user=user).first()

        if not password_change_request:
            return Response({"error": "No pending password change request found."}, status=status.HTTP_400_BAD_REQUEST)

        otp = random.randint(100000, 999999)
        password_change_request.otp = otp
        password_change_request.created_at = timezone.now()
        password_change_request.save()

        send_mail(
            subject='Password Change OTP - Resent',
            message=f"Your new OTP for password change is: {otp}",
            recipient_list=[user.email],
            from_email=settings.EMAIL_HOST_USER,
        )
        return Response({"message": "A new OTP has been sent to your email."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='verify-password-change')
    def verify_password_change(self, request):
        """
        Step 2: Verify OTP and change password.
        """
        otp = request.data.get('otp')

        if not otp:
            return Response({"error": "OTP is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        password_change_request = PasswordChangeRequest.objects.filter(user=user).first()

        if not password_change_request:
            return Response({"error": "No pending password change request found."}, status=status.HTTP_400_BAD_REQUEST)

        if str(password_change_request.otp) != str(otp):
            return Response({"error": "Incorrect OTP."}, status=status.HTTP_400_BAD_REQUEST)

        otp_age = (timezone.now() - password_change_request.created_at).total_seconds()
        if otp_age > 300:
            return Response({"error": "OTP has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)

        # Change the user's password
        user.password = make_password(password_change_request.new_password)
        user.save()

        password_change_request.delete()

        # Log out the user by invalidating the refresh token
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception as e:
                raise AuthenticationFailed('Refresh token is invalid or expired.')
        send_mail(
            subject='Password changed successfully',
            message=f'Password changed successfully and  you have been logged out. \n Login with your new password',
            recipient_list=[request.user.email],
            from_email=settings.EMAIL_HOST_USER,
        )
        return Response({"message": "Password changed successfully. You have been logged out."},
                        status=status.HTTP_200_OK)


class UserSignupViewSet(viewsets.ViewSet):
    """
    Viewset for handling user signup and OTP verification.
    """

    def create(self, request, *args, **kwargs):
        """
        Handles user signup.
        """
        serializer = UserSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        phone_number = serializer.validated_data['phone_number']

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

                return Response({"message": f"User already exists but is not verified. OTP resent."},
                                status=status.HTTP_200_OK)
            else:
                return Response({"error": "User already exists and is verified."}, status=status.HTTP_400_BAD_REQUEST)

        # Create new user
        otp = random.randint(100000, 999999)
        User.objects.create(
            first_name=serializer.validated_data['first_name'],
            last_name=serializer.validated_data['last_name'],
            email=email,
            password=make_password(password),
            phone_number=phone_number,
            otp=otp,
            otp_created_at=now()
        )

        send_mail(
            subject='Verify your email',
            message=f'Your OTP is: {otp}',
            recipient_list=[email],
            from_email=settings.EMAIL_HOST_USER,
        )

        return Response({"message": f"Signup successful. OTP sent to your email "}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='verify-otp')
    def verify_otp(self, request):
        """
        Verifies the OTP sent to the user's email.
        """
        serializer = UserSignupSerializerOTP(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if user.is_verified:
            return Response({"error": "User is already verified."}, status=status.HTTP_400_BAD_REQUEST)

        if str(user.otp) != otp:
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

        if now() - user.otp_created_at > datetime.timedelta(minutes=5):
            return Response({"error": "OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)

        user.is_verified = True
        user.otp = None
        user.save()

        send_mail(
            subject='Signup successful',
            message=f'You have finished the signup verification for ASLuxeryOriginals.com. Welcome!',
            recipient_list=[email],
            from_email=settings.EMAIL_HOST_USER,
        )

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        return Response({
            'message': 'Signup successful.',
            'access_token': access_token,
            'refresh_token': str(refresh),
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='resend-otp')
    def resend_otp(self, request):
        """
        Resends the OTP to the user's email.
        """
        serializer = UserSignupSerializerResendOTP(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if user.is_verified:
            return Response({"error": "User is already verified."}, status=status.HTTP_400_BAD_REQUEST)

        otp = random.randint(100000, 999999)
        user.otp = otp
        user.otp_created_at = now()
        user.save()

        send_mail(
            subject='Resend OTP',
            message=f'Your OTP is: {otp}',
            recipient_list=[email],
            from_email=settings.EMAIL_HOST_USER,
        )

        return Response({"message": f"OTP resent to your email."}, status=status.HTTP_200_OK)


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

        # Send login success email
        send_mail(
            subject='Login Successful',
            message=f'Your login to ASLuxeryOriginals.com was successful.',
            recipient_list=[email],
            from_email=settings.EMAIL_HOST_USER,
        )

        return Response({
            'message': 'Login successful.',
            'access_token': access_token,
            'refresh_token': str(refresh),
        }, status=status.HTTP_200_OK)


class LogoutViewSet(viewsets.ViewSet):
    """
    Handles user logout by invalidating refresh token.
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def logout(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if not refresh_token:
                return Response({"detail": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

            # Invalidate the refresh token
            token = RefreshToken(refresh_token)
            token.blacklist()  # This will invalidate the refresh token

            return Response({"detail": "Logout successful."}, status=status.HTTP_200_OK)
        except Exception as e:
            # Handle specific exceptions if necessary
            return Response({"detail": "Error during logout.", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
