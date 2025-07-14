from http import client
import pytest
from django.urls import reverse
from rest_framework import status
from api.models import Exam, Question
from rest_framework.utils.serializer_helpers import ReturnDict
from api.tests.conftest import admin_user, teacher

pytestmark = pytest.mark.django_db

def test_admin_can_crud_exam_and_questions(admin_user, auth_client, teacher):
    client = auth_client(admin_user)
    exam_url = reverse("exam-list")
    exam_data = {
        "title": "Maths Term Exam",
        "created_by": admin_user.id,
        "assigned_teacher": teacher.id,
        "start_time": "2025-12-31T10:00:00Z",
        "duration_minutes": 45,
    }
    resp = client.post(exam_url, exam_data, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    exam_id = resp.data["id"]

    detail_url = reverse("exam-detail", args=[exam_id])
    assert client.get(detail_url).status_code == 200

    resp = client.patch(detail_url, {"duration_minutes": 50}, format="json")
    assert resp.status_code == 200
    assert resp.data["duration_minutes"] == 50

    question_url = reverse("question-list")
    q_data = {
        "exam": exam_id,
        "text": "What is 2 + 2?",
        "option1": "2",
        "option2": "3",
        "option3": "4",
        "option4": "5",
        "correct_option": 3,
    }
    resp = client.post(question_url, q_data, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    question_id = resp.data["id"]

    question_detail = reverse("question-detail", args=[question_id])
    resp = client.get(question_detail)
    assert resp.status_code == 200
    assert isinstance(resp.data, dict)
    assert resp.data["text"].startswith("What is 2")

    resp = client.patch(question_detail, {"text": "Updated question?"})
    assert resp.status_code == 200
    assert "Updated" in resp.data["text"]

    assert client.delete(question_detail).status_code == 204

    assert client.delete(detail_url).status_code == 204

