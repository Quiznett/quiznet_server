from django.urls import path
from .views import (
    QuizCreateView,
    QuizDeleteView,
    AttemptStartView,
    AttemptSaveView,
    AttemptStatusView,
    AttemptSubmitView,
)

urlpatterns = [
    path('create/', QuizCreateView.as_view(), name='quiz-create'),
    path('delete/<uuid:quiz_id>/', QuizDeleteView.as_view()),

    #Attempt-related urls
    path('attempt/<uuid:quiz_id>/', AttemptStartView.as_view(), name='attempt-start'),
    path('attempt/<uuid:quiz_id>/save/', AttemptSaveView.as_view(), name='attempt-save'),
    path('attempt/<uuid:quiz_id>/status/', AttemptStatusView.as_view(), name='attempt-status'),
    path('attempt/<uuid:quiz_id>/submit/', AttemptSubmitView.as_view(), name='attempt-submit'),
]