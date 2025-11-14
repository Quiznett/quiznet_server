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
    permission_classes = [IsAuthenticated]
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
    
class QuizDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, quiz_id):
        try:
            quiz = Quiz.objects.get(quiz_id = quiz_id)
        except Quiz.DoesNotExist:
            return Response({"detail":"Quiz not found"}, status = status.HTTP_404_NOT_FOUND)
        
        if quiz.creator != request.user:
            return Response({"detail":"Not allowed"}, status = status.HTTP_403_FORBIDDEN)
        
        quiz.delete()
        return Response({"detail": "Quiz deleted successfully"}, status = status.HTTP_200_OK)

# class QuestionCreateView(APIView):
#     def post(self,request):
#         pass