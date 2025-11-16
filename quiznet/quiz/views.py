from .serializers import (
    QuizCreateSerializer, 
    QuizListSerializer, 
    AttemptStartSerializer, 
    AttemptQuestionSerializer, 
    QuestionSerializer, 
    AttemptSaveSerializer, 
    AttemptSubmitSerializer
)
from .models import Quiz, Attempt
from django.utils import timezone
from django.core.cache import cache

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import render
from rest_framework_simplejwt.tokens import RefreshToken,TokenError
from rest_framework.authentication import authenticate
# Create your views here.

class QuizCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self,request):
        serializer = QuizCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            quiz = serializer.save()
            return Response(QuizCreateSerializer(quiz).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self,request):
        quizzes = Quiz.objects.filter(creator=request.user).order_by('initiates_on')
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

class AttemptStartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, quiz_id):
        user = request.user

        try:
            quiz = Quiz.objects.get(quiz_id = quiz_id)
        except Quiz.DoesNotExist:
            return Response({"detail": "Quiz not found"}, status = status.HTTP_404_NOT_FOUND)


        if not quiz.is_active:
            return Response({"detail": "Quiz is not active."}, status = status.HTTP_403_FORBIDDEN)
        
        now = timezone.now()

        if now > quiz.ends_on:
            return Response({"detail": "Quiz has ended."}, status = status.HTTP_403_FORBIDDEN)
        

        attempt = Attempt.objects.filter(user = user, quiz=quiz).first()

        if attempt and attempt.is_submitted():
            return Response({"detail": "You have already submitted this quiz."}, status = status.HTTP_403_FORBIDDEN)
        
        if not attempt:
            attempt = Attempt.objects.create(user = user, quiz = quiz)

        
        cache_key = f"quiz_questions_{quiz.quiz_id}"
        cached_questions = cache.get(cache_key)

        if cached_questions is None:
            qs = quiz.questions.all()
            cached_questions = AttemptQuestionSerializer(qs, many = True).data
            cache.set(cache_key, cached_questions, timeout = 3600)

        data = AttemptStartSerializer(attempt).data
        data["questions"] = cached_questions

        return Response(data, status=status.HTTP_200_OK)


class AttemptSaveView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, quiz_id):
        user = request.user

        serializer = AttemptSaveSerializer(data = request.data)
        serializer.is_valid(raise_exception=True)
        question_id = str(serializer.validated_data["question_id"])
        selected_option = serializer.validated_data["selected_option"]

        try:
            quiz = Quiz.objects.get(quiz_id = quiz_id)
        except Quiz.DoesNotExist:
            return Response({"detail": "Quiz not found"}, status = status.HTTP_404_NOT_FOUND)
        

        attempt = Attempt.objects.filter(user = user, quiz=quiz).first()
        if not attempt:
            return Response({"detail": "attempt not found. Start attempt first."}, status = status.HTTP_400_BAD_REQUEST)
        

        if attempt.is_submitted():
            return Response({"detail": "You have already submitted this quiz."}, status = status.HTTP_403_FORBIDDEN)
        
        responses = attempt.responses or {}
        responses[question_id] = selected_option
        attempt.responses = responses
        attempt.save(update_fields=["responses"])

        return Response({"detail": "Answer saved."}, status = status.HTTP_200_OK)
    

class AttemptStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, quiz_id):
        user = request.user

        try: 
            quiz = Quiz.objects.get(quiz_id = quiz_id)
        except Quiz.DoesNotExist:
            return Response({"detail": "Quiz not found"}, status = status.HTTP_404_NOT_FOUND)
        

        now  = timezone.now()

        attempt = Attempt.objects.filter(user = user, quiz = quiz).first()
        already_submitted = attempt.is_submitted() if attempt else False

        quiz_ended = now > quiz.ends_on

        if quiz_ended and quiz.is_active:
            quiz.is_active = False
            quiz.save(update_fields = ["is_active"])

        return Response({
            "is_active": quiz.is_active,
            "quiz_ended": quiz_ended,
            "already_submitted": already_submitted,
            "now": now,
            "ends_on": quiz.ends_on,
        }, status = status.HTTP_200_OK)


class AttemptSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, quiz_id):
        user = request.user


        try:
            quiz = Quiz.objects.get(quiz_id = quiz_id)
        except Quiz.DoesNotExist:
            return Response({"detail": "Quiz not found"}, status = status.HTTP_404_NOT_FOUND)
        

        attempt = Attempt.objects.filter(user = user, quiz = quiz).first()
        if not attempt:
            return Response({"detail": "Attempt not found. Start the quiz first."}, status = status.HTTP_400_BAD_REQUEST)
        

        if attempt.is_submitted():
            return Response({"detail":"You have already submitted this quiz."}, status = status.HTTP_403_FORBIDDEN)
        
        final_score = attempt.grade()

        attempt.mark_submitted()

        quiz.user_scores.append({
            "user_id": str(user.id),
            "score": final_score
        })
        quiz.save(update_fields=["user_scores"])


        serializer = AttemptSubmitSerializer(attempt)
        return Response(serializer.data, status=status.HTTP_200_OK)


# class QuestionCreateView(APIView):
#     def post(self,request):
#         pass