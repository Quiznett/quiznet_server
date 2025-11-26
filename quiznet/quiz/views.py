"""
Author:
    - Kartikyea Singh Parihar
    - Ashvin Kausar
"""

from .serializers import (
    QuizCreateSerializer, 
    QuizListSerializer, 
    AttemptStartSerializer, 
    AttemptQuestionSerializer, 
    QuestionSerializer, 
    AttemptSaveSerializer, 
    AttemptSubmitSerializer,
    AttemptResponseSerializer
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
from django.contrib.auth import get_user_model

User = get_user_model()

# Create your views here.

class QuizCreateView(APIView):
    """
    Handles quiz creation and listing quizzes created by the authenticated user.

    POST: 
        Creates a new quiz using QuizCreateSerializer.

    GET:
        Returns all quizzes created by the logged-in user, ordered by initiates_on.
    """
    permission_classes = [IsAuthenticated]
    def post(self,request):
        """Create a new quiz."""
        serializer = QuizCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            quiz = serializer.save()
            return Response(QuizCreateSerializer(quiz).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self,request):
        """Return list of quizzes created by the authenticated user."""
        quizzes = Quiz.objects.filter(creator=request.user).order_by('initiates_on')
        serializer = QuizListSerializer(quizzes, many=True)
        return Response(serializer.data)
    
class QuizDeleteView(APIView):
    """
    Allows an authenticaed user to delete their own quiz.

    DELETE:
        Delete the quiz if it exists AND belongs to the authenticated user.
        Returns:
            - 200 OK on success
            - 404 if quiz not found
            - 403 if trying to delete someone else's quiz
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, quiz_id):
        """Delete a quiz created by the user."""
        try:
            quiz = Quiz.objects.get(quiz_id = quiz_id)
        except Quiz.DoesNotExist:
            return Response({"detail":"Quiz not found"}, status = status.HTTP_404_NOT_FOUND)
        
        if quiz.creator != request.user:
            return Response({"detail":"Not allowed"}, status = status.HTTP_403_FORBIDDEN)
        
        quiz.delete()
        return Response({"detail": "Quiz deleted successfully"}, status = status.HTTP_200_OK)

class AttemptStartView(APIView):
    """
    Initializer or retrieves an ongoin quiz attempt.

    GET: 
        - Validate quiz existence.
        - Ensures quiz is active and within time bounds.
        - Creates a new Attempt if one does not exist.
        - Returns: 
            - Attempt details via AttemptStartSerializer
            - All quiz questions (cached for better performance)

        - Errors: 
            - 404 Quiz not found
            - 403 Quiz inactive or ended 
            - 403 Attempt already submitted 
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, quiz_id):
        """Start or resume an attempt and return questions."""
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
    """
    Saves a single answer during an ongoing quiz attempt.

    PATCH: 
        - Requires question_id and selected_option. 
        - Stores/updates answer inside Attempt.responses.
        - Does NOT submit the quiz.
        - Ensures:
            - Quiz exists
            - Attempt is not submitted.

        Returns: 
            - 200 OK on success.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, quiz_id):
        """Save/update a user's answer for a question."""
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
    """
    Provides real-time status of the quiz and user's attempt.

    GET:
        - Checks if quiz has ended.
        - Automatically deactivates quiz when ends_on has passes.
        - Returns: 
            {
                "is_active" : bool,
                "quiz_ended" : bool,
                "already_submitted" : bool,
                "now" : datetime,
                "ends_on" : datetime
            }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, quiz_id):
        """Return live status of quiz and attempt."""
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
    """
    Finalizes a quiz attempt, calculates score and records it.

    POST:
        - Ensures quiz exists
        - Ensures attempt exists
        - Ensures attempt is not already submitted
        - Calculatates score via attempt.grade()
        - Marks attempt submitted
        - Appends {user_id, score} to quiz.user_scores

        Returns AttemptSubmitSerializer data.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, quiz_id):
        """Submit the full quiz attempt and return the score."""
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


class AttemptUserResponseView(APIView):
    """
    Handles fetching quiz attempt details for:
    - the current user, OR
    - any user (only if the quiz creator requests it).

    This endpoint supports two modes:
        1) /quiz/<quiz_id>/attempts/
           - If caller is quiz creator → return ALL users' attempts.
           - If caller is a normal user → return ONLY their own attempt.

        2) /quiz/<quiz_id>/attempts/<user_id>/
           - Only quiz creator can access another user’s attempt.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, quiz_id, user_id=None):

        # ---------------------------------------------
        # 1) Validate quiz existence
        # ---------------------------------------------
        try:
            quiz = Quiz.objects.get(quiz_id=quiz_id)
        except Quiz.DoesNotExist:
            return Response({"detail": "Quiz not found"}, status=status.HTTP_404_NOT_FOUND)

        # ---------------------------------------------
        # 2) If user_id is NOT provided
        # ---------------------------------------------
        if user_id is None:
            # If the requester is the creator, return ALL attempts for this quiz
            if quiz.creator == request.user:

                # Retrieve every attempt for this quiz
                # NOTE: You may want to filter only submitted attempts.
                attempts = Attempt.objects.filter(quiz=quiz)

                if not attempts.exists():
                    return Response({"detail": "No attempts found for this quiz"}, status=status.HTTP_404_NOT_FOUND)

                # Serialize all attempts
                serializer = AttemptResponseSerializer(attempts, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)

            # If the requester is NOT the creator, return only THEIR attempt
            target_user = request.user

        else:
            # ---------------------------------------------
            # 3) When a specific user_id IS provided
            # Only quiz creator can view another user's responses
            # ---------------------------------------------
            if quiz.creator != request.user:
                return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

            # Ensure target user exists
            try:
                target_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # ---------------------------------------------
        # 4) Fetch attempt for the target_user
        # ---------------------------------------------
        attempt = Attempt.objects.filter(user=target_user, quiz=quiz).first()

        if not attempt:
            return Response({"detail": "Attempt not found"}, status=status.HTTP_404_NOT_FOUND)

        # Ensure the attempt is submitted (if method exists)
        if hasattr(attempt, "is_submitted") and callable(attempt.is_submitted):
            if not attempt.is_submitted():
                return Response({"detail": "Attempt not submitted yet"}, status=status.HTTP_400_BAD_REQUEST)

        # Serialize single attempt
        serializer = AttemptResponseSerializer(attempt)
        return Response(serializer.data, status=status.HTTP_200_OK)



# -------------------------------------------------------------------
# New API: Return ONLY the quizzes that the current user has attempted
# -------------------------------------------------------------------

from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

# Using existing serializers from your project
from .serializers import QuizListSerializer, AttemptSubmitSerializer


class AttemptedQuizzesView(APIView):
    """
    Returns ALL quizzes that the current authenticated user has attempted.

    - Does NOT return the user's attempt details.
    - Only the QUIZ information is returned.
    - Uses QuizListSerializer for clean quiz summary output.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # ----------------------------------------------------------
        # 1) Query all Attempt records for this user
        #    and extract DISTINCT quiz primary keys
        # ----------------------------------------------------------
        quiz_pks = Attempt.objects.filter(
            user=user
        ).values_list('quiz__pk', flat=True).distinct()

        # If user has never attempted any quiz → return empty list
        if not quiz_pks:
            return Response([], status=status.HTTP_200_OK)

        # ----------------------------------------------------------
        # 2) Fetch those quizzes and order by initiates_on DESC
        # ----------------------------------------------------------
        quizzes = Quiz.objects.filter(pk__in=quiz_pks).order_by('-initiates_on')

        # Serialize quiz objects only
        serializer = QuizListSerializer(quizzes, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
