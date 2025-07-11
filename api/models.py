from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.username} ({self.role})"

class Teacher(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)
    subject_specialization = models.CharField(max_length=100)
    employee_id = models.CharField(max_length=20, unique=True)
    date_of_joining = models.DateField()
    status = models.CharField(max_length=10, choices=[('active', 'Active'), ('inactive', 'Inactive')])

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.subject_specialization}"

class Student(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)
    roll_number = models.CharField(max_length=20, unique=True)
    student_class = models.CharField(max_length=50)
    date_of_birth = models.DateField()
    admission_date = models.DateField()
    status = models.CharField(max_length=10, choices=[('active', 'Active'), ('inactive', 'Inactive')])
    assigned_teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)

    def delete(self, *args, **kwargs):
        user = self.user
        super().delete(*args, **kwargs)
        user.delete() 

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.roll_number}"
