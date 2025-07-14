import pytest
from rest_framework.test import APIRequestFactory
from api.serializers import StudentSerializer, ExamSubmissionSerializer, ExamCreateSerializer

from api.models import Student

pytestmark = pytest.mark.django_db 

def test_student_serializer_create(teacher):
    data = {
        "user": {
            "username": "u",
            "email": "u@x.com",
            "first_name": "U",
            "last_name": "Z",
            "password": "pass"
        },
        "phone": "555",
        "roll_number": "RX",
        "student_class": "8‑B",
        "date_of_birth": "2012-01-01",
        "admission_date": "2024-06-01",
        "status": "active",
        "assigned_teacher": teacher.id,
    }
    ser = StudentSerializer(data=data)
    assert ser.is_valid(), ser.errors
    obj = ser.save()
    assert isinstance(obj, Student)

def test_exam_create_auto_assign(teacher_user, teacher):
    factory = APIRequestFactory()
    request = factory.post("/")
    request.user = teacher_user
    data = {
        "title": "T",
        "start_time": "2025-01-01T00:00:00Z", 
        "duration_minutes": 5
    }
    serializer = ExamCreateSerializer(data=data, context={"request": request})
    assert serializer.is_valid(), serializer.errors
    exam = serializer.save()
    assert exam.assigned_teacher == teacher
