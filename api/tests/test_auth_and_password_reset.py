import re
import pytest
from django.urls import reverse
from django.core import mail
from rest_framework import status

pytestmark = pytest.mark.django_db

def test_jwt_login(student_user, api_client):
    url = reverse("token_obtain_pair")      
    resp = api_client.post(
        url, {"username": student_user.username, "password": "studpass"}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert "access" in resp.data and "refresh" in resp.data

def test_password_reset_flow(api_client, student_user, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    request_url = reverse("password-reset")   
    resp = api_client.post(request_url, {"email": student_user.email})
    assert resp.status_code == status.HTTP_200_OK
    assert len(mail.outbox) == 1
    body = mail.outbox[0].body
    uid, token = re.search(r"uid=([^&]+)&token=([^\s]+)", body).groups()
    confirm_url = reverse("password-reset-confirm") 
    resp2 = api_client.post(
        confirm_url,
        {"uid": uid, "token": token, "new_password": "NewPass123!"},
    )
    assert resp2.status_code == status.HTTP_200_OK
    assert resp2.data["detail"].lower().startswith("password has been reset")
