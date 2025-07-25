from .models import Exam
from rest_framework import serializers
from rest_framework import serializers
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str

from .models import CustomUser, Teacher, Student,Exam, ExamSubmission, Question, Answer

class BaseUserSerializer(serializers.ModelSerializer):
    username = serializers.CharField()

    class Meta:
        model = CustomUser
        fields = ["username", "email", "first_name", "last_name", "password", "role",]
        extra_kwargs = {"password": {"write_only": True},
        'role': {'read_only': True},
        }

    def validate_username(self, value):
        user_qs = CustomUser.objects.filter(username=value)
        if self.instance:
            user_qs = user_qs.exclude(pk=self.instance.pk)
        if user_qs.exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value
    
    def validate_email(self, value):
        email_qs = CustomUser.objects.filter(email=value)
        if self.instance:
            email_qs = email_qs.exclude(pk=self.instance.pk)
        if email_qs.exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def create(self, validated_data):
        password = validated_data.pop("password")
        user = CustomUser(**validated_data)
        user.role = self.context.get('role')
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
    
class TeacherSerializer(serializers.ModelSerializer):
    user = BaseUserSerializer()

    class Meta:
        model = Teacher
        fields = "__all__"

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        user_serializer = BaseUserSerializer(data=user_data, context={'role': 'teacher'})
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        return Teacher.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", None)
        if user_data:
            user_serializer = BaseUserSerializer(instance=instance.user, data=user_data, partial=self.partial)
            user_serializer.is_valid(raise_exception=True)
            user_serializer.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class StudentSerializer(serializers.ModelSerializer):
    user = BaseUserSerializer()

    class Meta:
        model = Student
        fields = "__all__"

    def validate(self, data):
        assigned_teacher = data.get("assigned_teacher")
        student_class = data.get("student_class")

        if assigned_teacher and assigned_teacher.assigned_class != student_class:
            raise serializers.ValidationError(
                "Assigned teacher must belong to the same class as the student."
            )
        return data

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        user_serializer = BaseUserSerializer(data=user_data, context={'role' : 'student'})
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        return Student.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", None)
        if user_data:
            user_serializer = BaseUserSerializer(instance=instance.user, data=user_data, partial=self.partial)
            user_serializer.is_valid(raise_exception=True)
            user_serializer.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class QuestionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Question
        fields = [
            "id", "exam", "text",
            "option1", "option2", "option3", "option4",
            "correct_option",
        ]
        read_only_fields = ["id"]

class QuestionPublicSerializer(serializers.ModelSerializer):

    class Meta:
        model  = Question
        fields = ["id", "text", "option1", "option2", "option3", "option4"]

class ExamMetaSerializer(serializers.ModelSerializer):

    class Meta:
        model  = Exam
        fields = [
            "id", "title", "scope",
            "target_standard", "target_class",
            "start_time", "duration_minutes",
            "created_by", "assigned_teacher",
        ]
        read_only_fields = ["id"]



class ExamCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = [
            "id",
            "title",
            "scope",
            "target_standard",
            "target_class",
            "start_time",
            "duration_minutes",
            "assigned_teacher",
        ]
        read_only_fields = ["id", "scope", "assigned_teacher"]

    def validate(self, attrs):
        user = self.context["request"].user

        if user.role == "admin":
            # Admin creates school-level exams
            attrs["scope"] = "school"
            attrs["assigned_teacher"] = None
            # attrs["target_standard"] = target.split("-")[0]

            if not attrs.get("target_standard"):
                raise serializers.ValidationError({
                    "target_standard": "This field is required for school-level exams."
                })

            if attrs.get("target_class"):
                raise serializers.ValidationError({
                    "target_class": "Admin should not set target_class for school-level exams."
                })

        elif user.role == "teacher":
            # Teacher creates class-level exams
            teacher = getattr(user, "teacher", None)
            if not teacher:
                raise serializers.ValidationError("Teacher profile not found.")

            if not attrs.get("target_class"):
                raise serializers.ValidationError({
                    "target_class": "This field is required for class-level exams."
                })

            if attrs["target_class"] != teacher.assigned_class:
                raise serializers.ValidationError({
                    "target_class": "You can only create exams for your assigned class."
                })

            attrs["scope"] = "class"
            attrs["assigned_teacher"] = teacher
            attrs["target_standard"] = None  # Not needed for class-level

        else:
            raise serializers.ValidationError("Only admin or teacher can create exams.")

        return attrs

    def create(self, validated_data):
        return Exam.objects.create(
            created_by=self.context["request"].user, **validated_data
        )



class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Answer
        fields = ["question", "selected_option"]


class AnswerResultSerializer(serializers.ModelSerializer):
    question_text  = serializers.CharField(source="question.text", read_only=True)
    option1 = serializers.CharField(source="question.option1", read_only=True)
    option2 = serializers.CharField(source="question.option2", read_only=True)
    option3 = serializers.CharField(source="question.option3", read_only=True)
    option4 = serializers.CharField(source="question.option4", read_only=True)
    correct_option = serializers.IntegerField(source="question.correct_option", read_only=True)
    is_correct     = serializers.SerializerMethodField()

    def get_is_correct(self, obj):
        return obj.selected_option == obj.question.correct_option

    class Meta:
        model  = Answer
        fields = [
            "question", "question_text",
             "option1", "option2", "option3", "option4",
            "selected_option", "correct_option",
            "is_correct",
        ]


class ExamSubmissionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, write_only=True)
    student_roll_number = serializers.CharField(source="student.roll_number", read_only=True)
    

    class Meta:
        model  = ExamSubmission
        fields = ["id", "exam", "answers", "score", "student"]
        read_only_fields = ["id", "score" , "student"]

    def create(self, validated_data):

        answers_data = validated_data.pop("answers")        
        submission = ExamSubmission.objects.create(**validated_data)
        answers = [
            Answer(
                submission=submission,
                question=item["question"],
                selected_option=item["selected_option"],
            )
            for item in answers_data
        ]
        Answer.objects.bulk_create(answers)

        submission.score = sum(
            1 for ans in answers if ans.selected_option == ans.question.correct_option
        )
        submission.save()
        return submission


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user with this email.")
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid           = serializers.CharField()
    token         = serializers.CharField()
    new_password  = serializers.CharField(min_length=6)

    def validate(self, attrs):
        try:
            uid  = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = CustomUser.objects.get(pk=uid)
        except (ValueError, CustomUser.DoesNotExist):
            raise serializers.ValidationError("Invalid link")

        if not PasswordResetTokenGenerator().check_token(user, attrs["token"]):
            raise serializers.ValidationError("Invalid or expired token")

        attrs["user"] = user
        return attrs

    def save(self):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user

class ExamSubmissionResultSerializer(serializers.ModelSerializer):
    exam_title = serializers.CharField(source="exam.title", read_only=True)
    student_name = serializers.SerializerMethodField()
    student_roll_number = serializers.CharField(source="student.roll_number", read_only=True)
    created_by = serializers.CharField(source="exam.created_by.username", read_only=True)
    answers = AnswerResultSerializer(many=True, read_only=True)

    def get_student_name(self, obj):
        return f"{obj.student.user.first_name} {obj.student.user.last_name}"

    class Meta:
        model = ExamSubmission
        fields = ["id",
            "exam",
            "exam_title",
            "created_by",
            "student",
            "student_name",
            "student_roll_number",
            "score",
            "submitted_at",
            "answers",
            ]
        