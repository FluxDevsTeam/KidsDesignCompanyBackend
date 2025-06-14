from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group 

User = get_user_model()


class GroupSerializer(serializers.ModelSerializer):
    ''' Django built in Group model serializer to create role
    e.g ['storekeeper', 'shopkeeper', ... ] '''

    class Meta:
        model = Group
        fields = ['id', 'name']
        read_only_fields = ['id']

class ForgotPasswordRequestSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6, required=True)
    email = serializers.EmailField(required=True)
    new_password = serializers.CharField(write_only=True, required=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=True, min_length=8)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs


class UserProfileSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6, required=False)
    new_email = serializers.CharField(write_only=True, required=False, min_length=8)
    new_first_name = serializers.CharField(write_only=True, required=False, min_length=2)
    new_last_name = serializers.CharField(write_only=True, required=False, min_length=2)
    new_phone_number = serializers.CharField(write_only=True, required=False, min_length=11)
    password = serializers.CharField(write_only=True, required=False)


class ViewUserProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'phone_number',]


class PasswordChangeRequestSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6, required=True)
    old_password = serializers.CharField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=True, min_length=8)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs


class UserSignupSerializer(serializers.ModelSerializer):
    roles = serializers.SlugRelatedField(
        source='groups',
        queryset=Group.objects.all(),
        slug_field='name',
        many=True,
        required=False
    )
    password = serializers.CharField(write_only=True, min_length=8, required=True)
    verify_password = serializers.CharField(write_only=True, min_length=8, required=True)

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'phone_number', 'email', 'password', 'verify_password', 'roles']
        read_only_fields = ['id']

    def __init__(self, *args, **kwargs):
        """
        Remove password fields on update.
        """
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields.pop('password', None)
            self.fields.pop('verify_password', None)


    def validate(self, data):
        """
        Ensure that password and verify_password match but don't check during updates
        """
        if not self.instance and data['password'] != data['verify_password']:
                raise serializers.ValidationError("Passwords do not match.")
        return data

    def update(self, instance, validated_data):
        """
        Prevent updating sensitive fields during the update.
        """
        validated_data.pop('password', None)
        validated_data.pop('verify_password', None)
        roles = validated_data.pop('groups', [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.groups.set(roles)
        instance.save()

        return instance

    def to_representation(self, instance):
        """
        Customize the serialized output to exclude sensitive data.
        """
        representation = super().to_representation(instance)
        representation.pop('password', None)
        representation.pop('verify_password', None)
        return representation


class UserSignupSerializerOTP(serializers.Serializer):
    otp = serializers.CharField(max_length=6)
    email = serializers.EmailField()


class UserSignupSerializerResendOTP(serializers.Serializer):
    email = serializers.EmailField()


class LoginSerializer(serializers.ModelSerializer):
    password = serializers.CharField(max_length=50, min_length=6, write_only=True)
    email = serializers.EmailField(max_length=50, min_length=2)

    class Meta:
        model = User
        fields = ['email', 'password']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email')
        read_only_fields = ['email', ]


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=100)


class CheckOTPSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6)
    token = serializers.CharField()


class CheckSignupOTPSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6)
    token = serializers.CharField()
