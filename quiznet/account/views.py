from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import serializers
from rest_framework.response import Response
from account.serializers import RegisterSerializer,LoginSerializer,LogoutSerializer
from rest_framework_simplejwt.tokens import RefreshToken,TokenError
from rest_framework.authentication import authenticate
from rest_framework import status
class RegisterView(APIView):
    def post(self,request):
        serializer = RegisterSerializer(data=request.data)
        if(serializer.is_valid()):
            user=serializer.save()
            refresh = RefreshToken.for_user(user)
            response = Response({
                "message": "User registered successfully!",
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "fullname":user.first_name+" "+user.last_name,
                    "created_at": user.date_joined
                }
            }, status=status.HTTP_201_CREATED)

            response.set_cookie(
            key="access",
            value=str(refresh.access_token),
            httponly=True,
            secure=True,       # production me https ke liye
            samesite="Lax",
            max_age=300        # 5 minutes
)
            
            response.set_cookie(
            key="refresh",
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=864000     # 10 days
        )
            response.set_cookie(
            key="user",
            value={"user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "fullname":user.first_name+" "+user.last_name,
                    "created_at": user.date_joined
                }},
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=864000     # 10 days
        )
            
            return response
    
        return Response(serializer.errors)
    
class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        user = authenticate(username=username, password=password)

        if user is not None:
            # create JWT tokens for the user
            refresh = RefreshToken.for_user(user)
            response = Response({
                "message": "User LoggedIn successfully!",
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "fullname":user.first_name+" "+user.last_name,
                    "created_at": user.date_joined
                }
            }, status=status.HTTP_201_CREATED)

            response.set_cookie(
            key="access",
            value=str(refresh.access_token),
            httponly=True,
            secure=True,       # production me https ke liye
            samesite="Lax",
            max_age=300        # 5 minutes
)
            
            response.set_cookie(
            key="refresh",
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=864000     # 10 days
        )
            response.set_cookie(
            key="user",
            value={"user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "fullname":user.first_name+" "+user.last_name,
                    "created_at": user.date_joined
                }},
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=864000     # 10 days
        )
            
            return response
    
        else:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data['refresh']

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()  # invalidate this token
            return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)
        except TokenError:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)