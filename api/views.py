import csv
from io import TextIOWrapper
from datetime import timedelta
from django.http import HttpResponse
from django.utils import timezone
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import GenericAPIView 
from rest_framework import viewsets, permissions, serializers, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from api.permissions import IsAdmin, IsStudent, IsTeacher
from .models import CustomUser, Teacher, Student, Exam, ExamSubmission, Question
from .serializers import PasswordResetConfirmSerializer, PasswordResetRequestSerializer, QuestionPublicSerializer, TeacherExamCreateSerializer, TeacherSerializer, StudentSerializer, ExamSerializer, ExamCreateSerializer, ExamSubmissionSerializer, QuestionCreateSerializer


class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer

    def get_permissions(self):
        role = getattr(self.request.user, "role", None)
        if role == "admin":
            return [permissions.IsAuthenticated(), IsAdmin()]
        if role == "teacher" and self.action in ["me", "my_students", "student_results"]:
            return [permissions.IsAuthenticated(), IsTeacher()]
        raise PermissionDenied("Not allowed.")

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "role", None) == "admin":
            return Teacher.objects.all()
        if getattr(user, "role", None) == "teacher":
            return Teacher.objects.filter(user=user)
        return Teacher.objects.none()
    
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def student_results(self, request):
        teacher = Teacher.objects.get(user=request.user)
        submissions = ExamSubmission.objects.filter(student__assigned_teacher=teacher).select_related("exam", "student")
        serializer = ExamSubmissionSerializer(submissions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="me", permission_classes=[IsTeacher])
    def me(self, request):
        teacher = Teacher.objects.filter(user=request.user).first()
        if not teacher:
            return Response({"detail": "Teacher profile not found."}, status=404)
        return Response(self.get_serializer(teacher).data)

    @action(detail=False, methods=["get"], url_path="me/students", permission_classes=[IsTeacher])
    def my_students(self, request):
        teacher = Teacher.objects.filter(user=request.user).first()
        if not teacher:
            return Response({"detail": "Teacher profile not found."}, status=404)

        students = Student.objects.filter(assigned_teacher=teacher).order_by("id")
        page = self.paginate_queryset(students)
        if page is not None:
            return self.get_paginated_response(StudentSerializer(page, many=True).data)
        return Response(StudentSerializer(students, many=True).data)

    @action(detail=False, methods=["get"], url_path="export", permission_classes=[IsAdmin])
    def export_csv(self, request):
        teachers = self.get_queryset()

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="teachers.csv"'

        writer = csv.writer(response)
        writer.writerow(["Username", "Email", "Phone", "Subject", "Employee ID", "Status"])

        for t in teachers:
            writer.writerow([
                t.user.username,
                t.user.email,
                t.phone,
                t.subject_specialization,
                t.employee_id,
                t.status,
            ])
        return response

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, "role", None)
        if role == "admin":
            return Student.objects.all()
        if role == "teacher":
            return Student.objects.filter(assigned_teacher__user=user)
        if role == "student":
            return Student.objects.filter(user=user)
        return Student.objects.none()

    def get_permissions(self):
        role = getattr(self.request.user, "role", None)
        if role == "admin":
            return [permissions.IsAuthenticated(), IsAdmin()]
        if role == "teacher" and self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated(), IsTeacher()]
        if role == "student" and self.action in ["me", "my_marks"]:
            return [permissions.IsAuthenticated(), IsStudent()]
        raise PermissionDenied("Not allowed.")
    

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def my_marks(self, request):
        student = Student.objects.get(user=request.user)
        submissions = ExamSubmission.objects.filter(student=student).select_related("exam")
        serializer = ExamSubmissionSerializer(submissions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="me", permission_classes=[IsStudent])
    def me(self, request):
        student = Student.objects.filter(user=request.user).first()
        if not student:
            return Response({"detail": "Student profile not found."}, status=404)
        return Response(self.get_serializer(student).data)

    @action(detail=False, methods=["get"], url_path="export", permission_classes=[IsAdmin])
    def export_csv(self, request):
        students = self.get_queryset()

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="students.csv"'

        writer = csv.writer(response)
        writer.writerow(["Username", "Email", "Phone", "Assigned Teacher", "Status"])

        for s in students:
            writer.writerow([
                s.user.username,
                s.user.email,
                s.phone,
                s.assigned_teacher.user.username if s.assigned_teacher else "",
                s.status,
            ])
        return response
    
    @action(detail=False, methods=["post"], url_path="import", parser_classes=[MultiPartParser], permission_classes=[IsAdmin])
    def import_csv(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "CSV file is required."}, status=400)

        decoded = TextIOWrapper(file, encoding="utf-8")
        reader  = csv.DictReader(decoded)

        created, errors = [], []

        for row_no, row in enumerate(reader, start=1):
            try:
                user_data = {
                    "username":    row["username"],
                    "email":       row["email"],
                    "first_name":  row["first_name"],
                    "last_name":   row["last_name"],
                    "password":    row["password"],
                }
                teacher_id = row.get("assigned_teacher_id")
                teacher = Teacher.objects.get(id=int(teacher_id)) if teacher_id else None
                student_data = {
                    "user":            user_data,
                    "phone":           row["phone"],
                    "roll_number":     row["roll_number"],
                    "student_class":   row["student_class"],
                    "date_of_birth":   row["date_of_birth"],   
                    "admission_date":  row["admission_date"],  
                    "status":          row.get("status", "active"),
                    "assigned_teacher": teacher.id if teacher else None,
                }

                serializer = StudentSerializer(data=student_data)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                created.append(serializer.data)
            except Exception as exc:
                errors.append(f"Row {row_no}: {exc}")

        return Response({"created": created, "errors": errors},
                        status=201 if created else 400)

class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.select_related("assigned_teacher")
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            if self.request.user.role == "teacher":
                return TeacherExamCreateSerializer 
            return ExamCreateSerializer          
        return ExamSerializer
    
    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        role = getattr(self.request.user, "role", None)
        if role == "admin":
            return [permissions.IsAuthenticated(), IsAdmin()]
        if role == "teacher":
            return [permissions.IsAuthenticated(), IsTeacher()]
        raise PermissionDenied("Not allowed.")
    
    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return self.queryset
        if user.role == "teacher":
            return self.queryset.filter(assigned_teacher__user=user)
        if user.role == "student":
            if hasattr(Exam, "students"):
                return self.queryset.filter(students__user=user)
            return self.queryset.filter(assigned_teacher=user.student.assigned_teacher)
        return Exam.objects.none()

    def perform_create(self, serializer):
        serializer.save()


class ExamSubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = ExamSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ExamSubmission.objects.filter(student__user=self.request.user)

    def perform_create(self, serializer):
        student = Student.objects.get(user=self.request.user)
        exam = serializer.validated_data['exam']
        now = timezone.now()

        if ExamSubmission.objects.filter(exam=exam, student=student).exists():
            raise serializers.ValidationError(
                "You have already submitted this exam."
            )

        if exam.assigned_teacher != student.assigned_teacher:
            raise PermissionDenied("You are not assigned to this exam.")

        if now > exam.start_time + timedelta(minutes=exam.duration_minutes):
            raise serializers.ValidationError("Exam time is over.")

        serializer.save(student=student)

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.select_related("exam__assigned_teacher")
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return QuestionCreateSerializer
        return QuestionPublicSerializer
    
    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]

        role = getattr(self.request.user, "role", None)
        if role == "admin":
            return [permissions.IsAuthenticated(), IsAdmin()]
        if role == "teacher":
            return [permissions.IsAuthenticated(), IsTeacher()]
        raise PermissionDenied("Not allowed.")

    def get_queryset(self):
        qs   = super().get_queryset()
        user = self.request.user
        if user.role == "teacher":
            return qs.filter(exam__assigned_teacher__user=user)
        if user.role == "student":
            return qs.filter(exam__students__user=user) | qs.filter(
                exam__assigned_teacher=user.student.assigned_teacher
            )
        return qs

class PasswordResetRequestView(GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = []  

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = CustomUser.objects.get(email=serializer.validated_data["email"])
        token = PasswordResetTokenGenerator().make_token(user)
        uid   = urlsafe_base64_encode(force_bytes(user.pk))

        reset_url = (
            f'{settings.FRONTEND_RESET_URL}?uid={uid}&token={token}'
        )

        send_mail(
            subject="Password reset",
            message=f"Use this link to reset your password:\n{reset_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

        return Response({"detail": "Password‑reset e‑mail sent."},
                        status=status.HTTP_200_OK)

class PasswordResetConfirmView(GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = []

    def post(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"detail": "Password has been reset."},
                        status=status.HTTP_200_OK)
    
