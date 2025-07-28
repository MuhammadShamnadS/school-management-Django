from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from .validators import validate_roll_number, validate_employee_id,validate_phone_number,validate_name,validate_date_of_birth

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )
    first_name = models.CharField(max_length=50, validators=[validate_name])
    last_name = models.CharField(max_length=50, validators=[validate_name], blank=True, null=True )
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    

    def __str__(self):
        return f"{self.username} ({self.role})"
    
# Teacher model    
class Teacher(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    phone = models.CharField(max_length=10, validators=[validate_phone_number])
    subject_specialization = models.CharField(max_length=100)
    employee_id = models.CharField(max_length=20, unique=True, validators=[validate_employee_id])
    date_of_joining = models.DateField()
    status = models.CharField(max_length=10, choices=[('active', 'Active'), ('inactive', 'Inactive')])
    assigned_class = models.CharField(max_length=10)  

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.subject_specialization} ({self.assigned_class})"

    def delete(self, *args, **kwargs):
        user = self.user
        super().delete(*args, **kwargs)
        user.delete()

# student model
class Student(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    phone = models.CharField(max_length=10, validators=[validate_phone_number])
    roll_number = models.CharField(max_length=3, validators=[validate_roll_number])
    student_class = models.CharField(max_length=10)  # e.g., '1-A'
    date_of_birth = models.DateField(validators=[validate_date_of_birth])
    admission_date = models.DateField()
    status = models.CharField(max_length=10, choices=[('active', 'Active'), ('inactive', 'Inactive')])
    assigned_teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)

    # checkes roll number for each class is unique
    class Meta:
        unique_together = ('roll_number', 'student_class')
        ordering = ["id"]

    # checks the assigned teacher belongs to the same class of that student
    def clean(self):
        if self.assigned_teacher and self.assigned_teacher.assigned_class != self.student_class:
            raise ValidationError("Assigned teacher must belong to the same class as the student.")

    def delete(self, *args, **kwargs):
        user = self.user
        super().delete(*args, **kwargs)
        user.delete()

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.roll_number} ({self.student_class})"
    
# Exam model
class Exam(models.Model):
    SCOPE_CHOICES = (
        ("school", "School_level"),
        ("class", "Class_level"),
    )

    title = models.CharField(max_length=200)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    assigned_teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="exams", null=True, blank=True)
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    target_standard = models.CharField(max_length=10, null=True,blank=True)  
    target_class = models.CharField(max_length=10, null=True,blank=True)     
    start_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=5)

    # validate exam creation based on scope
    def clean(self):
        if self.scope == "school":
            if self.assigned_teacher:
                raise ValidationError("School-level exams cannot have an assigned teacher.")
            if not self.target_standard:
                raise ValidationError("School-level exams require a target_standard.")
            if self.target_class:
                raise ValidationError("School-level exams cannot have a target_class.")
        elif self.scope == "class":
            if not self.assigned_teacher:
                raise ValidationError("Class-level exams must have an assigned teacher.")
            if not self.target_class:
                raise ValidationError("Class-level exams require a target_class.")
            if self.assigned_teacher.assigned_class != self.target_class:
                raise ValidationError("Assigned teacher does not belong to the target_class.")
            if self.target_standard:
                raise ValidationError("Class-level exams cannot have a target_standard.")
        else:
            raise ValidationError("Invalid scope value.")
        
    # validate eligible students for attending an exam
    def eligible_students(self):
        if self.scope == "school":
            return Student.objects.filter(student_class__startswith=self.target_standard, status='active')
        else:
            return Student.objects.filter(
                assigned_teacher=self.assigned_teacher,
                student_class=self.target_class,
                status='active'
            )

    def __str__(self):
        return self.title

# Question model
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
    
# Exam sybmission model
class ExamSubmission(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)
    score = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True) 

    # ensure one submission per student for an exam
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['exam', 'student'], name='one_submission_per_exam')
        ]

    def __str__(self):
        return f"{self.student} - {self.exam}"
    
# Answer model    
class Answer(models.Model):
    submission = models.ForeignKey(ExamSubmission, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.IntegerField()

    def __str__(self):
        return f"Answer for {self.question} by {self.submission.student}"