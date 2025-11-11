from .serializers import QuizCreateSerializer, QuizListSerializer
from .models import Quiz
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from rest_framework.views import APIView
# Create your views here.
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken,TokenError
from rest_framework.authentication import authenticate
from rest_framework import status

class QuizCreateView(APIView):
    permisson_classes = [IsAuthenticated]
    def post(self,request):
        serializer = QuizCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            quiz = serializer.save()
            return Response(QuizCreateSerializer(quiz).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self,request):
        quizzes = Quiz.objects.all().order_by('initiates_on')
        serializer = QuizListSerializer(quizzes, many=True)
        return Response(serializer.data)


# class QuestionCreateView(APIView):
#     def post(self,request):
#         pass