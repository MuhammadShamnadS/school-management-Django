from rest_framework import serializers
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str

from .models import CustomUser, Teacher, Student,Exam, ExamSubmission, Question, Answer

class TeacherUserSerializer(serializers.ModelSerializer):

    class Meta:
        model  = CustomUser
        fields = ["username", "email", "first_name", "last_name", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated):
        pwd = validated.pop("password")
        user = CustomUser(**validated)
        user.set_password(pwd)
        user.role = "teacher"
        user.save()
        return user

class StudentUserSerializer(serializers.ModelSerializer):

    username = serializers.CharField(validators=[])  

    class Meta:
        model  = CustomUser
        fields = ["username", "email", "first_name", "last_name", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate_username(self, value):
        if self.instance and self.instance.username == value:
            return value
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with that username already exists.")
        return value

    def create(self, validated):
        pwd = validated.pop("password")
        user = CustomUser(**validated)
        user.set_password(pwd)
        user.role = "student"
        user.save()
        return user

    def update(self, instance, validated):
        password = validated.pop("password", None)
        for attr, val in validated.items():
            setattr(instance, attr, val)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class TeacherSerializer(serializers.ModelSerializer):
    user = TeacherUserSerializer()

    class Meta:
        model  = Teacher
        fields = "__all__"

    def create(self, validated):
        user_data = validated.pop("user")
        user = TeacherUserSerializer().create(user_data)
        return Teacher.objects.create(user=user, **validated)

    def update(self, instance, validated):
        user_data = validated.pop("user", {})
        for k, v in user_data.items():
            setattr(instance.user, k, v)
        instance.user.save()

        for k, v in validated.items():
            setattr(instance, k, v)
        instance.save()
        return instance

class StudentSerializer(serializers.ModelSerializer):
    user = StudentUserSerializer()

    class Meta:
        model  = Student
        fields = "__all__"

    def create(self, validated):
        user_data = validated.pop("user")
        user = StudentUserSerializer().create(user_data)
        return Student.objects.create(user=user, **validated)

    def update(self, instance, validated):
        user_data = validated.pop("user", None)
        if user_data:
            nested = StudentUserSerializer(instance=instance.user,
                                           data=user_data,
                                           partial=self.partial)
            nested.is_valid(raise_exception=True)
            nested.save()

        for k, v in validated.items():
            setattr(instance, k, v)
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
        model  = Exam
        fields = ["id", "title", "target_standard", "start_time", "duration_minutes"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        user = self.context["request"].user
        if user.role != "admin":
            raise serializers.ValidationError("Only admin may use this endpoint.")
        if not attrs.get("target_standard"):
            raise serializers.ValidationError(
                {"target_standard": "School‑level exam requires target_standard."}
            )
        attrs["scope"] = "school"
        attrs["assigned_teacher"] = None
        return attrs

    def create(self, attrs):
        return Exam.objects.create(created_by=self.context["request"].user, **attrs)


class TeacherExamCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model  = Exam
        fields = ["id", "title", "target_class", "start_time", "duration_minutes"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        user = self.context["request"].user
        if user.role != "teacher":
            raise serializers.ValidationError("Only teacher may use this endpoint.")

        target_cls = attrs.get("target_class")
        if not target_cls:
            raise serializers.ValidationError(
                {"target_class": "Class‑level exam requires target_class."}
            )

        valid_classes = Student.objects.filter(
            assigned_teacher=user.teacher
        ).values_list("student_class", flat=True).distinct()

        if target_cls not in valid_classes:
            raise serializers.ValidationError(
                {"target_class": "You can create exams only for classes you teach."}
            )

        attrs["scope"]            = "class"
        attrs["assigned_teacher"] = user.teacher
        return attrs

    def create(self, attrs):
        return Exam.objects.create(created_by=self.context["request"].user, **attrs)


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Answer
        fields = ["question", "selected_option"]


class AnswerResultSerializer(serializers.ModelSerializer):
    question_text  = serializers.CharField(source="question.text", read_only=True)
    correct_option = serializers.IntegerField(source="question.correct_option", read_only=True)
    is_correct     = serializers.SerializerMethodField()

    def get_is_correct(self, obj):
        return obj.selected_option == obj.question.correct_option

    class Meta:
        model  = Answer
        fields = [
            "question", "question_text",
            "selected_option", "correct_option",
            "is_correct",
        ]


class ExamSubmissionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, write_only=True)

    class Meta:
        model  = ExamSubmission
        fields = ["id", "exam", "answers", "score"]
        read_only_fields = ["id", "score"]

    def create(self, validated_data):

        answers_data = validated_data.pop("answers")
        student      = validated_data["student"]          
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
