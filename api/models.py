from django.contrib.auth.models import AbstractUser
from django.db import migrations, models


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

    def delete(self, *args, **kwargs):
        user = self.user           # keep ref
        super().delete(*args, **kwargs)
        user.delete() 
        
class Student(models.Model):
    class Meta:
        ordering = ["id"] 
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
    

class Exam(models.Model):
    SCOPE_CHOICES = (
        ("school", "School‑level"),   
        ("class",  "Class‑level"),    
    )

    title             = models.CharField(max_length=200)
    created_by        = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    assigned_teacher  = models.ForeignKey(Teacher, on_delete=models.CASCADE,related_name="exams",null=True, blank=True)
    scope             = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    target_standard   = models.CharField(max_length=10, blank=True)  # e.g. "10"
    target_class      = models.CharField(max_length=10, blank=True)  # e.g. "10‑A"
    start_time        = models.DateTimeField()
    duration_minutes  = models.IntegerField(default=5)

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.scope == "school":
            if self.assigned_teacher:
                raise ValidationError("School‑level exam must have no assigned_teacher")
            if not self.target_standard:
                raise ValidationError("School‑level exam requires target_standard")
        elif self.scope == "class":
            if not self.assigned_teacher:
                raise ValidationError("Class‑level exam must have assigned_teacher")
            if not self.target_class:
                raise ValidationError("Class‑level exam requires target_class")
        else:
            raise ValidationError("Invalid scope")

    def eligible_students(self):
        if self.scope == "school":
            return Student.objects.filter(student_class__startswith=self.target_standard)
        return Student.objects.filter(
            assigned_teacher=self.assigned_teacher,
            student_class=self.target_class,
        )

    def __str__(self):
        return self.title

class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    option1 = models.CharField(max_length=255)
    option2 = models.CharField(max_length=255)
    option3 = models.CharField(max_length=255)
    option4 = models.CharField(max_length=255)
    correct_option = models.IntegerField(choices=[(1, 'A'), (2, 'B'), (3, 'C'), (4, 'D')])

    def __str__(self):
        return self.text

class ExamSubmission(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)
    score = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["exam", "student"],
                name="one_submission_per_exam"
            )
        ]

    def __str__(self):
        return f"{self.student} - {self.exam}"

class Answer(models.Model):
    submission = models.ForeignKey(ExamSubmission, on_delete=models.CASCADE, related_name='answers', )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.IntegerField()
