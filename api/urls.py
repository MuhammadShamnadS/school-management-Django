from rest_framework.routers import DefaultRouter
from .views import TeacherViewSet, StudentViewSet
from django.urls import path, include

router = DefaultRouter(trailing_slash=False)
router.register(r'teachers', TeacherViewSet, basename='teacher')
router.register(r'students', StudentViewSet, basename='student')

urlpatterns = [
    path('', include(router.urls)),
]
