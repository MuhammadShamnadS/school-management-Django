from rest_framework.routers import DefaultRouter
from .views import TeacherViewSet, StudentViewSet, ExamViewSet, QuestionViewSet, ExamSubmissionViewSet, PasswordResetRequestView, PasswordResetConfirmView
from django.urls import path, include

router = DefaultRouter(trailing_slash=False)
router.register(r'teachers', TeacherViewSet, basename='teacher')
router.register(r'students', StudentViewSet, basename='student')
router.register(r'exams', ExamViewSet, basename='exam')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'submissions', ExamSubmissionViewSet, basename='submission')

urlpatterns = [
    path('', include(router.urls)),
    path('password-reset',           PasswordResetRequestView.as_view(),
         name='password-reset'),
    path('password-reset/confirm',   PasswordResetConfirmView.as_view(),
         name='password-reset-confirm'),
]
