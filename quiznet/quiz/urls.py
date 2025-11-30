"""
Author:
    - Kartikyea Singh Parihar
    - Ashvin Kausar
"""
from django.urls import path
from .views import (
    QuizCreateView,
    QuizDeleteView,
    AttemptStartView,
    AttemptSaveView,
    AttemptStatusView,
    AttemptSubmitView,
    AttemptUserResponseView,
    AttemptedQuizzesView,
    QuizInfoView
    
)

urlpatterns = [
    path('create/', QuizCreateView.as_view(), name='quiz-create'),
    path('delete/<uuid:quiz_id>/', QuizDeleteView.as_view()),

    #Attempt-related urls
    path('attempt/<uuid:quiz_id>/', AttemptStartView.as_view(), name='attempt-start'),
    path('attempt/<uuid:quiz_id>/save/', AttemptSaveView.as_view(), name='attempt-save'),
    path('attempt/<uuid:quiz_id>/status/', AttemptStatusView.as_view(), name='attempt-status'),
    path('attempt/<uuid:quiz_id>/submit/', AttemptSubmitView.as_view(), name='attempt-submit'),
    
    #Response-related urls
    path("quizzes/<uuid:quiz_id>/responses/", AttemptUserResponseView.as_view()),
    path("quizzes/<uuid:quiz_id>/responses/<uuid:user_id>/", AttemptUserResponseView.as_view()),
    path('quizzes/attempted/', AttemptedQuizzesView.as_view(), name='quizzes-attempted'),
    path('<uuid:quiz_id>/info/', QuizInfoView.as_view(), name='quiz-info'),
]