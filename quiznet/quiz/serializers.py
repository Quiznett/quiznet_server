"""
Author:
    - Kartikyea Singh Parihar
    - Ashvin Kausar
"""
from rest_framework import serializers
from django.utils import timezone
from .models import Quiz, Question, Attempt 

class QuestionSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying a Question.
    Used when creating a quiz and when returning all quiz questions.

    Excludes:
        - quiz (to avoid nesting quiz inside questions)
    """
    class Meta:
        model = Question
        exclude = ['quiz']

class AttemptQuestionSerializer(serializers.ModelSerializer):
    """
    Serializer for quiz questions during an attempt.

    Important:
        - Hides the correct answer field to prevent cheating.
        - Hides the parent quiz field.
    """
    class Meta:
        model = Question
        exclude = ['quiz', 'answer']

class QuizCreateSerializer(serializers.ModelSerializer):
    """
    Handles creation of a quiz along with nested questions.

    Input:
        - questions (write_only): List of questions to create

    Output:
        - questions_readable (read_only): Same questions after creation

    Additional Behaviour: 
        - Sets creator to request.user
        - Creates nested Question objects
        - Populates quiz.questions_id with created Question UUIDs
    """
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
        """Create a Quiz and its nested Question objects."""
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
    """
    Lightweight serializer for listing quizzes.

    Adds:  
        - question_count: Number of questions in the quiz
    """
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
        """Return number of questions in the quiz."""
        return obj.questions.count()


class UserScoreSerializer(serializers.Serializer):
    """
    Serializer for individual user score entries inside Quiz.user_scores.

    Fields:
        - user_id: UUID of user
        - score: integer score
    """
    user_id = serializers.UUIDField()
    score = serializers.IntegerField(min_value=0)

class QuestionIdSerializer(serializers.Serializer):
    """
    Simple serializer for question UUID references in Quiz.questions_id list. 
    """
    question_id  = serializers.UUIDField()

class QuizSerializer(serializers.ModelSerializer):
    """
    Full serializer for reading a Quiz with score and question references.

    Fields: 
        - user_scores: list of {user_id, score}
        - question_id: list of {question_id}
    """
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
    """
    Serializer used when the user starts or resumes a quiz attempt

    Returns:
        - quiz metadata (title, times, time limit)
        - user attempt info 
        - list of questions (hidden answers)
    """
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
        """Retturn all questions of the quiz without correct answeres."""
        qs = Question.objects.filter(quiz=obj.quiz)
        return AttemptQuestionSerializer(qs, many=True).data
    

class AttemptSaveSerializer(serializers.Serializer):
    """
    Serializer for saving a single response during an attempt.

    Fields:
        - question_id: UUID of question
        - selected_option: integer from 1 to 4
    """
    question_id = serializers.UUIDField()
    selected_option = serializers.IntegerField(min_value = 1, max_value = 4)

class AttemptSubmitSerializer(serializers.ModelSerializer):
    """
    Serializer returned after quiz submission

    Includes:
        - attempt_id
        - score
        - submitted_at timestamp
        - responses (dictionary: question_id -> selected option)
    """
    class Meta:
        model = Attempt
        fields = ["attempt_id", "score", "submitted_at", "responses"]

class AttemptResponseSerializer(serializers.ModelSerializer):
    # use CharField for safety in case user.id is not UUID type
    user_id = serializers.CharField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.SerializerMethodField()
    responses = serializers.SerializerMethodField()   # 👈 override to return detailed data

    class Meta:
        model = Attempt
        fields = [
            "attempt_id",
            "user_id",
            "username",
            "full_name",
            "score",
            "submitted_at",
            "responses",   # now this is the detailed structure
        ]

    def get_full_name(self, obj):
        first = (obj.user.first_name or "").strip()
        last = (obj.user.last_name or "").strip()
        full = f"{first} {last}".strip()
        return full or obj.user.username

    def get_responses(self, obj):
        """
        Returns a list of detailed responses like:
        [
          {
            "question_id": "...",
            "question_title": "...",
            "option1": "...",
            "option2": "...",
            "option3": "...",
            "option4": "...",
            "selected_option": 2,
            "correct_option": 3,
            "is_correct": false
          },
          ...
        ]
        """
        from .models import Question  # local import to avoid circular issues

        raw_responses = obj.responses or {}   # {question_id_str: selected_option}
        # Fetch all questions for this quiz in one query
        questions = Question.objects.filter(quiz=obj.quiz)
        question_map = {str(q.question_id): q for q in questions}

        detailed = []

        for qid_str, selected in raw_responses.items():
            q = question_map.get(qid_str)
            if not q:
                continue

            try:
                selected_int = int(selected)
            except (TypeError, ValueError):
                selected_int = None

            detailed.append({
                "question_id": qid_str,
                "question_title": q.question_title,
                "option1": q.option1,
                "option2": q.option2,
                "option3": q.option3,
                "option4": q.option4,
                "selected_option": selected_int,
                "correct_option": q.answer,
                "is_correct": (selected_int == q.answer) if selected_int is not None else False,
            })

        return detailed