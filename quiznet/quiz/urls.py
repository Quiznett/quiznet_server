from django.urls import path
from .views import QuizCreateView,QuizDeleteView

urlpatterns = [
    path('create/', QuizCreateView.as_view(), name='quiz-create'),
    path('delete/<uuid:quiz_id>/', QuizDeleteView.as_view()),
]