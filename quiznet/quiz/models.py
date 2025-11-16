import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

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
    
class Attempt(models.Model):
    attempt_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts")
    quiz = models.ForeignKey("Quiz", on_delete=models.CASCADE, related_name="attempts")

    responses = models.JSONField(default=dict)

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null = True, blank = True)
    score = models.IntegerField(null = True, blank = True)

    class Meta:
        indexes = [
            models.Index(fields=["user","quiz"]),
        ]

    def is_submitted(self):
        return self.submitted_at is not None
    
    def mark_submitted(self, when=None):
        self.submitted_at = when or timezone.now()
        self.save(update_fields=["submitted_at"])

    def grade(self):
        from .models import Question

        correct = 0

        for qid_str, selected in (self.responses or {}).items():
            try:
                q = Question.objects.get(question_id = qid_str, quiz = self.quiz)
            except Question.DoesNotExist:
                continue

            if q.answer == int(selected):
                correct += 1

        self.score = correct
        self.save(update_fields=["score"])
        return self.score
    
    def __str__(self):
        return f"Attempt {self.attempt_id} by {self.user} on {self.quiz}"