from rest_framework import serializers
from .models import Quiz
from quiz.models import Question

class UserScoreSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    score = serializers.IntegerField(min_value=0)

class QuestionIdSerializer(serializers.Serializer):
    question_id  = serializers.UUIDField()

class QuizSerializer(serializers.ModelSerializer):
    user_scores = UserScoreSerializer(many=True)
    questions_id = QuestionIdSerializer(many=True)

    class Meta:
        model = Quiz
        fields = ["quiz_id", "creator", "user_scores","questions_id","quiz_title", "is_active", "issued_date", "initiates_on"]



class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = "__all__"
