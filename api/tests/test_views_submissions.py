import pytest
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

pytestmark = pytest.mark.django_db

def test_student_submit_and_block_duplicate(
    student_user, auth_client, student, exam, questions
):

    client = auth_client(student_user)
    url = reverse("submission-list")

    answers = [{"question": q.id, "selected_option": 4} for q in questions]
    payload = {"exam": exam.id, "answers": answers}

    assert client.post(url, payload, format="json").status_code == status.HTTP_201_CREATED

    assert client.post(url, payload, format="json").status_code == status.HTTP_400_BAD_REQUEST

def test_late_submission_block(student_user, auth_client, student, exam, questions):
    exam.start_time = timezone.now() - timedelta(minutes=10)
    exam.save(update_fields=["start_time"])

    client = auth_client(student_user)
    url = reverse("submission-list")
    answers = [{"question": q.id, "selected_option": 4} for q in questions]
    resp = client.post(url, {"exam": exam.id, "answers": answers}, format="json")

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
