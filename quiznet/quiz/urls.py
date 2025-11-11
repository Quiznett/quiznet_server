from django.urls import path
from .views import QuizCreateView

urlpatterns = [
    path('create/', QuizCreateView.as_view(), name='quiz-create'),
]