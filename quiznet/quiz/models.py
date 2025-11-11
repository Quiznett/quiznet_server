from django.db import models
import uuid
from django.conf import settings

class Quiz(models.Model):
    quiz_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quizzes")

    # Stores list of objects like:
    # [
    #   {"user_id": "uuid-string", "score": 80},
    #   {"user_id": "uuid-string", "score": 95}
    # ]
    user_scores = models.JSONField(default=list)
    quiz_title = models.CharField(blank=False,max_length=200)
    is_active = models.BooleanField(default=True)
    issued_date = models.DateTimeField(auto_now_add=True)
    initiates_on = models.DateTimeField()
    ends_on = models.DateTimeField()
    time_limit_minutes = models.PositiveBigIntegerField()
    questions_id = models.JSONField(default=list)

    def __str__(self):
        return f"Quiz {self.quiz_id} by {self.creator}"


class Question(models.Model):
    question_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey("Quiz", on_delete=models.CASCADE, related_name="questions")

    question_title = models.CharField(max_length=2048)

    option1 = models.CharField(max_length=300)
    option2 = models.CharField(max_length=300)
    option3 = models.CharField(max_length=300)
    option4 = models.CharField(max_length=300)

    # Stores 1, 2, 3, or 4
    answer = models.PositiveSmallIntegerField(choices=[(1, "Option 1"), (2, "Option 2"), (3, "Option 3"), (4, "Option 4")])

    def __str__(self):
        return f"Q: {self.question_title[:50]}..."