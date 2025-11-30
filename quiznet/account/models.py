from django.db import models
from django.utils import timezone
from datetime import timedelta

class EmailOTP(models.Model):
    email = models.EmailField()  # removed unique=True
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        now = timezone.now()
        created = self.created_at

        if timezone.is_naive(created):
            created = timezone.make_aware(created)

        return now > created + timedelta(minutes=5)

    def str(self):
        return f"{self.email} - {self.otp}"