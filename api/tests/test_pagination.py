import pytest
from rest_framework import status
from django.urls import reverse
from api.models import CustomUser, Student

@pytest.mark.django_db

def test_students_list_pagination(admin_user, auth_client, teacher):
    for i in range(7):
        user = CustomUser.objects.create_user(
            username=f"s{i}",
            password="pass123",
            role="student"
        )
        Student.objects.create(
            user=user,
            phone="1234567890",
            roll_number=f"RX{i}",
            student_class="10-A",
            date_of_birth="2010-01-01",
            admission_date="2024-06-01",
            status="active",
            assigned_teacher=teacher,
        )

    client = auth_client(admin_user)
    url = reverse("student-list")
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 7
    assert "next" in response.data
    assert response.data["next"] is not None
    assert isinstance(response.data["results"], list)
    assert len(response.data["results"]) <= 5
