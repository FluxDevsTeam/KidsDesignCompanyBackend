from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group 

User = get_user_model()


class GroupSerializer(serializers.ModelSerializer):
    ''' Django built-in Group model serializer to create roles
    e.g. ['shopkeeper', 'project_manager', 'factory_manager', 'ceo', 'storekeeper'] '''

    GROUP_CHOICES = (
        ('shopkeeper', 'shopkeeper'),
        ('project_manager', 'project_manager'),
        ('factory_manager', 'factory_manager'),
        ('ceo', 'ceo'),
        ('storekeeper', 'storekeeper'),
        ('admin', 'admin'),
        ('accountant', 'accountant'),
    )

    name = serializers.ChoiceField(choices=GROUP_CHOICES, required=True)

    class Meta:
        model = Group
        fields = ['id', 'name']
        read_only_fields = ['id']

    def validate_name(self, value):
        if Group.objects.filter(name=value).exists() and not self.instance:
            raise serializers.ValidationError(f"Group with name '{value}' already exists.")
        return value


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


class LoginSerializer(serializers.ModelSerializer):
    password = serializers.CharField(max_length=50, min_length=6, write_only=True)
    email = serializers.EmailField(max_length=50, min_length=2)

    class Meta:
        model = User
        fields = ['email', 'password']
