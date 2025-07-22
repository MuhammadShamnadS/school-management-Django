import csv
from io import TextIOWrapper
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from api.permissions import IsAdmin, IsStudent, IsTeacher
from .models import CustomUser, Teacher, Student, Exam, ExamSubmission, Question
from .serializers import (
    ExamMetaSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    TeacherSerializer,
    StudentSerializer,
    ExamCreateSerializer,
    QuestionCreateSerializer,
    QuestionPublicSerializer,
    ExamSubmissionSerializer,
)



class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer

    # Permissions
    def get_permissions(self):
        role = getattr(self.request.user, "role", None)
        if role == "admin":
            return [permissions.IsAuthenticated(), IsAdmin()]
        if role == "teacher" and self.action in ["me", "my_students", "student_results"]:
            return [permissions.IsAuthenticated(), IsTeacher()]
        raise PermissionDenied("Not allowed.")


    # Query‑set filtering
    def get_queryset(self):
        user = self.request.user
        if getattr(user, "role", None) == "admin":
            return Teacher.objects.all()
        if getattr(user, "role", None) == "teacher":
            return Teacher.objects.filter(user=user)
        return Teacher.objects.none()


    @action(detail=False, methods=["get"], url_path="me", permission_classes=[IsTeacher])
    def me(self, request):
        teacher = Teacher.objects.filter(user=request.user).first()
        if not teacher:
            return Response({"detail": "Teacher profile not found."}, status=404)
        return Response(self.get_serializer(teacher).data)

    @action(detail=False,methods=["get"],url_path="me/students",permission_classes=[IsTeacher],)
    def my_students(self, request):
        teacher = Teacher.objects.filter(user=request.user).first()
        if not teacher:
            return Response({"detail": "Teacher profile not found."}, status=404)

        students = Student.objects.filter(assigned_teacher=teacher).order_by("id")
        page = self.paginate_queryset(students)
        if page is not None:
            return self.get_paginated_response(StudentSerializer(page, many=True).data)
        return Response(StudentSerializer(students, many=True).data)

    @action(detail=False,methods=["get"],url_path="student-results",permission_classes=[IsTeacher])
    def student_results(self, request):
        teacher = Teacher.objects.get(user=request.user)
        subs = (
            ExamSubmission.objects.filter(student__assigned_teacher=teacher)
            .select_related("exam", "student")
            .order_by("exam_id", "student_id")
        )
        return Response(ExamSubmissionSerializer(subs, many=True).data)
    
    @action(detail=True, methods=["get"], url_path="students", permission_classes=[IsAdmin])
    def students_under_teacher(self, request, pk=None):
        try:
            teacher = Teacher.objects.get(pk=pk)
        except Teacher.DoesNotExist:
            return Response({"detail": "Teacher not found."}, status=404)

        students = Student.objects.filter(assigned_teacher=teacher).order_by("id")
        page = self.paginate_queryset(students)
        if page is not None:
            return self.get_paginated_response(StudentSerializer(page, many=True).data)
        return Response(StudentSerializer(students, many=True).data)


    @action(detail=False, methods=["get"], url_path="export", permission_classes=[IsAdmin])
    def export_csv(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="teachers.csv"'
        writer = csv.writer(response)
        writer.writerow(
            ["Username", "Email", "Phone", "Subject", "Employee ID", "Status"]
        )
        for t in self.get_queryset():
            writer.writerow(
                [
                    t.user.username,
                    t.user.email,
                    t.phone,
                    t.subject_specialization,
                    t.employee_id,
                    t.status,
                ]
            )
        return response


class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer

    def get_permissions(self):
        role = getattr(self.request.user, "role", None)
        if role == "admin":
            return [permissions.IsAuthenticated(), IsAdmin()]
        if role == "teacher" and self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated(), IsTeacher()]
        if role == "student" and self.action in ["me", "my_marks"]:
            return [permissions.IsAuthenticated(), IsStudent()]
        raise PermissionDenied("Not allowed.")

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

    @action(detail=False, methods=["get"], url_path="me", permission_classes=[IsStudent])
    def me(self, request):
        student = Student.objects.filter(user=request.user).first()
        if not student:
            return Response({"detail": "Student profile not found."}, status=404)
        return Response(self.get_serializer(student).data)

    @action(detail=False, methods=["get"], permission_classes=[IsStudent])
    def my_marks(self, request):
        student = Student.objects.get(user=request.user)
        subs = (
            ExamSubmission.objects.filter(student=student)
            .select_related("exam")
            .order_by("exam_id")
        )
        return Response(ExamSubmissionSerializer(subs, many=True).data)

    @action(detail=False, methods=["get"], url_path="export", permission_classes=[IsAdmin])
    def export_csv(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="students.csv"'
        writer = csv.writer(response)
        writer.writerow(["Username", "Email", "Phone", "Assigned Teacher", "Status"])
        for s in self.get_queryset():
            writer.writerow(
                [
                    s.user.username,
                    s.user.email,
                    s.phone,
                    s.assigned_teacher.user.username if s.assigned_teacher else "",
                    s.status,
                ]
            )
        return response

    @action(
        detail=False,
        methods=["post"],
        url_path="import",
        parser_classes=[MultiPartParser],
        permission_classes=[IsAdmin],
    )
    def import_csv(self, request):

        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "CSV file is required."}, status=400)

        decoded = TextIOWrapper(file, encoding="utf-8")
        reader = csv.DictReader(decoded)

        created, errors = [], []

        for row_no, row in enumerate(reader, start=1):
            try:
                user_data = {
                    "username": row["username"],
                    "email": row["email"],
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "password": row["password"],
                }
                teacher_id = row.get("assigned_teacher_id")
                teacher = (
                    Teacher.objects.get(id=int(teacher_id)) if teacher_id else None
                )
                student_data = {
                    "user": user_data,
                    "phone": row["phone"],
                    "roll_number": row["roll_number"],
                    "student_class": row["student_class"],
                    "date_of_birth": row["date_of_birth"],
                    "admission_date": row["admission_date"],
                    "status": row.get("status", "active"),
                    "assigned_teacher": teacher.id if teacher else None,
                }
                ser = StudentSerializer(data=student_data)
                ser.is_valid(raise_exception=True)
                ser.save()
                created.append(ser.data)
            except Exception as exc:  
                errors.append(f"Row {row_no}: {exc}")

        status_code = status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST
        return Response({"created": created, "errors": errors}, status=status_code)

class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.select_related("assigned_teacher")
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ExamCreateSerializer
        return ExamMetaSerializer


    def get_permissions(self):
        if self.action in ("list", "retrieve", "questions"):
            return [permissions.IsAuthenticated()]
        if self.request.user.role == "admin":
            return [permissions.IsAuthenticated(), IsAdmin()]
        if self.request.user.role == "teacher":
            return [permissions.IsAuthenticated(), IsTeacher()]
        raise PermissionDenied("Not allowed.")

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.role == "admin":
            return qs
        if user.role == "teacher":
            cls = user.teacher.assigned_class
            std = cls.split("-")[0]
            return qs.filter(
                Q(scope="class", assigned_teacher=user.teacher) |
                Q(scope="school", target_standard=std)
            )
        if user.role == "student":
            stu = user.student
            std = stu.student_class.split("-")[0]
            return qs.filter(
                Q(scope="school", target_standard=std) |
                Q(scope="class", target_class=stu.student_class, assigned_teacher=stu.assigned_teacher)
            )
        return Exam.objects.none()

    def _owns_exam(self, exam):
        u = self.request.user
        if u.role == "admin":
            return exam.scope == "school" and exam.created_by_id == u.id
        if u.role == "teacher":
            return exam.scope == "class" and exam.assigned_teacher_id == u.teacher.id
        return False

    def perform_update(self, serializer):
        if not self._owns_exam(self.get_object()):
            raise PermissionDenied("Not allowed to edit this exam.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self._owns_exam(instance):
            raise PermissionDenied("Not allowed to delete this exam.")
        instance.delete()

    @action(detail=True, methods=["get", "post"], url_path="questions")
    def questions(self, request, pk=None):
        exam = self.get_object()
        user = request.user

        # GET - Return questions list
        if request.method == "GET":
            if user.role == "student" and user.student not in exam.eligible_students():
                raise PermissionDenied("Not allowed to view questions.")

            qs = exam.questions.all().order_by("id")
            serializer_class = (
                QuestionCreateSerializer if user.role in ["admin", "teacher"]
                else QuestionPublicSerializer
            )
            return Response(serializer_class(qs, many=True).data)

        # POST - Add a new question to the exam
        if request.method == "POST":
            if user.role not in ["admin", "teacher"]:
                raise PermissionDenied("Only admin/teacher can add questions.")

            serializer = QuestionCreateSerializer(data=request.data)
            if serializer.is_valid():
                # Ensure the user owns the exam (check your _owns_exam logic)
                if not self._owns_exam(exam):
                    raise PermissionDenied("You cannot add questions to this exam.")
                serializer.save(exam=exam)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExamSubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = ExamSubmissionSerializer
    permission_classes = [IsAuthenticated,IsStudent]

    def get_queryset(self):
        return ExamSubmission.objects.filter(student__user=self.request.user)

    def perform_create(self, serializer):
        try:
            student = Student.objects.get(user=self.request.user)
        except Student.DoesNotExist:
            raise PermissionDenied("Only students can submit exams")
        exam = serializer.validated_data["exam"]
        now = timezone.now()

        if ExamSubmission.objects.filter(exam=exam, student=student).exists():
            raise serializers.ValidationError("You have already submitted this exam.")

        if student not in exam.eligible_students():
            raise PermissionDenied("You are not allowed to take this exam.")

        if now > exam.start_time + timedelta(minutes=exam.duration_minutes):
            raise serializers.ValidationError("Exam time is over.")

        serializer.save(student=student)

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.select_related("exam__created_by", "exam__assigned_teacher")
    permission_classes = [IsAuthenticated]

    # -------- choose serializer
    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return QuestionCreateSerializer
        user = self.request.user
        if user.is_authenticated and user.role in ["admin", "teacher"]:
            return QuestionCreateSerializer
        return QuestionPublicSerializer

    # -------- custom permission logic
    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        role = getattr(self.request.user, "role", None)
        if role == "admin":
            return [permissions.IsAuthenticated(), IsAdmin()]
        if role == "teacher":
            return [permissions.IsAuthenticated(), IsTeacher()]
        raise PermissionDenied("Not allowed.")

    # -------- Ownership helper
    def _owns_exam(self, exam):
        user = self.request.user
        if user.role == "admin":
            return exam.created_by_id == user.id
        if user.role == "teacher":
            return exam.assigned_teacher_id == getattr(user, "teacher", None).id
        return False

    # -------- CRUD guards
    def perform_create(self, serializer):
        if not self._owns_exam(serializer.validated_data["exam"]):
            raise PermissionDenied("You cannot add questions to this exam.")
        serializer.save()

    def perform_update(self, serializer):
        if not self._owns_exam(serializer.instance.exam):
            raise PermissionDenied("You cannot modify questions of this exam.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self._owns_exam(instance.exam):
            raise PermissionDenied("You cannot delete questions of this exam.")
        instance.delete()

    # -------- Query‑set restriction for list/retrieve
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == "teacher":
            return qs.filter(exam__assigned_teacher__user=user)
        if user.role == "student":
            stu = user.student
            std = stu.student_class.split("-")[0]
            return qs.filter(
                Q(exam__scope="school", exam__target_standard=std)
                | Q(
                    exam__scope="class",
                    exam__target_class=stu.student_class,
                    exam__assigned_teacher=stu.assigned_teacher,
                )
            )
        return qs


#  PASSWORD RESET

class PasswordResetRequestView(GenericAPIView):

    serializer_class = PasswordResetRequestSerializer
    permission_classes = []

    def post(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user = CustomUser.objects.get(email=ser.validated_data["email"])
        token = PasswordResetTokenGenerator().make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_url = f"{settings.FRONTEND_RESET_URL}?uid={uid}&token={token}"

        send_mail(
            "Password reset",
            f"Use this link to reset your password:\n{reset_url}",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )

        return Response({"detail": "Password‑reset e‑mail sent."}, status=200)


class PasswordResetConfirmView(GenericAPIView):

    serializer_class = PasswordResetConfirmSerializer
    permission_classes = []

    def post(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"detail": "Password has been reset."}, status=200)
