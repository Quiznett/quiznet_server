from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions

class RegisterSerializer(serializers.ModelSerializer):
    fullname = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        # date_joined is read-only so it's OK to include for response
        fields = ['username', 'email', 'fullname', 'password', 'date_joined']
        read_only_fields = ['date_joined']

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with that username already exists.")
        return value

    def validate_email(self, value):
        # optional: enforce unique email if you want
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with that email already exists.")
        return value

    def validate(self, data):
        # Run Django's password validators
        password = data.get('password')
        try:
            validate_password(password)
        except exceptions.ValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        return data

    def create(self, validated_data):
        fullname = validated_data.pop('fullname', '')
        first_name, last_name = self.split_fullname(fullname)

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', None),
            password=validated_data['password'],
            first_name=first_name,
            last_name=last_name
        )
        return user

    def split_fullname(self, fullname):
        parts = fullname.strip().split(" ", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return parts[0] if parts else "", ""


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


# NOTE: If you place the refresh token in an HttpOnly cookie (recommended),
# the client will NOT send the refresh token in the request body. So a serializer
# that expects `refresh` is misleading. Make logout endpoint read the cookie.
# To reflect that, keep LogoutSerializer empty (no required fields).
class LogoutSerializer(serializers.Serializer):
    # no fields required when refresh token is stored in HttpOnly cookie
    pass
