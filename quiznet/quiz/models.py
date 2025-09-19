import uuid
from django.db import models
from django.contrib.auth.models import User  # Or your custom User model

# Create your models here.
class Quiz(models.Model):
    quiz_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    