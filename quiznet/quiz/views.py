from django.shortcuts import render
from rest_framework.views import APIView
# Create your views here.
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken,TokenError
from rest_framework.authentication import authenticate
from rest_framework import status

class QuizCreateView(APIView):
    def post(self,request):
        pass
    def get(self,request):
        pass

class QuestionCreateView(APIView):
    def post(self,request):
        pass