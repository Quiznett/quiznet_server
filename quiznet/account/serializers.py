
from rest_framework import serializers
from django.contrib.auth.models import User

class RegisterSerializer(serializers.ModelSerializer):
    fullname = serializers.CharField(write_only=True)  # user gives this
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'fullname', 'password','date_joined']
        read_only_fields = ['date_joined']

    def create(self, validated_data):
        fullname = validated_data.pop('fullname')
        first_name, last_name = self.split_fullname(fullname)

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email'),
            password=validated_data['password'],
            first_name=first_name,
            last_name=last_name
        )
        return user

    def split_fullname(self, fullname):
        parts = fullname.strip().split(" ", 1)
        if len(parts) == 2:
            return parts[0], parts[1]  # first_name, last_name
        return parts[0], ""  # if only one word is given
    

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()