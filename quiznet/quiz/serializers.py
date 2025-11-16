from rest_framework import serializers
from django.utils import timezone
from .models import Quiz, Question, Attempt 

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        exclude = ['quiz']

class AttemptQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        exclude = ['quiz', 'answer']

class QuizCreateSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, write_only=True)
    questions_readable = QuestionSerializer(source='questions', many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            'quiz_id',
            'creator',
            'quiz_title',
            'initiates_on',
            'ends_on',
            'time_limit_minutes',
            'questions',
            'questions_readable',
            'is_active',
        ]
        read_only_fields = ['quiz_id', 'creator', 'questions_readable']

    def create(self, validated_data):
        questions_data = validated_data.pop('questions', [])
        creator = self.context['request'].user
        quiz = Quiz.objects.create(creator=creator, **validated_data)

        question_ids = []
        for q_data in questions_data:
            question = Question.objects.create(quiz=quiz, **q_data)
            question_ids.append(str(question.question_id))

        quiz.questions_id = question_ids
        quiz.save()
        return quiz


class QuizListSerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Quiz
        fields = [
            'quiz_id',
            'quiz_title',
            'initiates_on',
            'ends_on',
            'time_limit_minutes',
            'is_active',
            'question_count',
        ]

    def get_question_count(self, obj):
        return obj.questions.count()


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
        fields = ["quiz_id", 
                  "creator", 
                  "user_scores",
                  "questions_id",
                  "quiz_title", 
                  "is_active", 
                  "issued_date", 
                  "initiates_on",
                  "ends_on",
                  "time_limit_minutes"
                 ]


class AttemptStartSerializer(serializers.ModelSerializer):
    quiz_id = serializers.UUIDField(source="quiz.quiz_id", read_only=True)
    quiz_title = serializers.CharField(source="quiz.quiz_title", read_only=True)
    time_limit_minutes = serializers.IntegerField(source="quiz.time_limit_minutes", read_only=True)
    initiates_on = serializers.DateTimeField(source="quiz.initiates_on", read_only = True)
    ends_on = serializers.DateTimeField(source="quiz.ends_on", read_only=True)

    questions = serializers.SerializerMethodField()

    class Meta:
        model = Attempt
        fields = [
            "attempt_id",
            "quiz_id",
            "quiz_title",
            "started_at",
            "responses",
            "time_limit_minutes",
            "initiates_on",
            "ends_on",
            "questions"
        ]
    
    def get_questions(self, obj):
        qs = Question.objects.filter(quiz=obj.quiz)
        return AttemptQuestionSerializer(qs, many=True).data
    

class AttemptSaveSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    selected_option = serializers.IntegerField(min_value = 1, max_value = 4)

class AttemptSubmitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attempt
        fields = ["attempt_id", "score", "submitted_at", "responses"]