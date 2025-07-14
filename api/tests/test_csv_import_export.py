import pytest
from rest_framework import status
from django.urls import reverse

pytestmark = pytest.mark.django_db

def test_student_csv_import(admin_user, auth_client, sample_csv):
    client = auth_client(admin_user)
    url = reverse("student-list") + "/import"    
    with sample_csv.open("rb") as fh:
        resp = client.post(url, {"file": fh}, format="multipart")
    assert resp.status_code == status.HTTP_201_CREATED
    assert len(resp.data["created"]) == 2
    assert resp.data["errors"] == []

def test_teacher_csv_export(admin_user, auth_client, teacher):
    client = auth_client(admin_user)
    url = reverse("teacher-export-csv")           
    resp = client.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp["Content-Type"].startswith("text/csv")
    assert "Username,Email,Phone" in resp.content.decode().splitlines()[0]
