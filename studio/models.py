from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = [("student", "Ученик"), ("teacher", "Преподаватель"), ("admin", "Администратор")]
    role = models.CharField(max_length=12, choices=ROLE_CHOICES, default="student")
    phone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return self.get_full_name() or self.username

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    registered_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return str(self.user)

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher_profile")
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="teachers/", blank=True)
    def __str__(self): return str(self.user)

class Direction(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    def __str__(self): return self.name

class Level(models.Model):
    name = models.CharField(max_length=60, unique=True)
    order = models.PositiveSmallIntegerField(default=1)
    description = models.TextField(blank=True)
    def __str__(self): return self.name

class StudentLevel(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="levels")
    direction = models.ForeignKey(Direction, on_delete=models.CASCADE)
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    approved_by = models.ForeignKey(Teacher, null=True, blank=True, on_delete=models.SET_NULL)
    approved_at = models.DateTimeField(default=timezone.now)
    class Meta: unique_together = ("student", "direction")
    def __str__(self): return f"{self.student} — {self.direction}: {self.level}"

class DanceGroup(models.Model):
    name = models.CharField(max_length=100)
    direction = models.ForeignKey(Direction, on_delete=models.PROTECT)
    level = models.ForeignKey(Level, on_delete=models.PROTECT)
    teacher = models.ForeignKey(Teacher, on_delete=models.PROTECT)
    capacity = models.PositiveIntegerField(default=12, validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)
    def __str__(self): return self.name

class Hall(models.Model):
    name = models.CharField(max_length=80)
    capacity = models.PositiveIntegerField(default=20)
    description = models.TextField(blank=True)
    def __str__(self): return self.name

class Schedule(models.Model):
    WEEKDAYS = [(0,"Понедельник"),(1,"Вторник"),(2,"Среда"),(3,"Четверг"),(4,"Пятница"),(5,"Суббота"),(6,"Воскресенье")]
    group = models.ForeignKey(DanceGroup, on_delete=models.CASCADE, related_name="schedules")
    hall = models.ForeignKey(Hall, on_delete=models.PROTECT)
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)

class Lesson(models.Model):
    STATUS = [("planned","Запланировано"),("done","Проведено"),("cancelled","Отменено")]
    group = models.ForeignKey(DanceGroup, on_delete=models.CASCADE, related_name="lessons")
    hall = models.ForeignKey(Hall, on_delete=models.PROTECT)
    starts_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    status = models.CharField(max_length=12, choices=STATUS, default="planned")
    def __str__(self): return f"{self.group} — {self.starts_at:%d.%m.%Y %H:%M}"

class Subscription(models.Model):
    STATUS = [("active","Активен"),("expired","Истёк"),("used","Израсходован")]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="subscriptions")
    direction = models.ForeignKey(Direction, on_delete=models.PROTECT)
    starts_on = models.DateField()
    ends_on = models.DateField()
    visits_total = models.PositiveIntegerField(default=8)
    visits_used = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=12, choices=STATUS, default="active")
    @property
    def remaining(self): return max(0, self.visits_total - self.visits_used)
    def __str__(self): return f"{self.student} — {self.direction}"

class Booking(models.Model):
    STATUS = [("booked","Записан"),("cancelled","Отменён"),("attended","Посетил"),("missed","Неявка")]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="bookings")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="bookings")
    subscription = models.ForeignKey(Subscription, on_delete=models.PROTECT)
    status = models.CharField(max_length=12, choices=STATUS, default="booked")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: unique_together = ("student", "lesson")
    def __str__(self): return f"{self.student} → {self.lesson}"

class Attendance(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="attendance")
    was_present = models.BooleanField(default=False)
    marked_by = models.ForeignKey(Teacher, null=True, on_delete=models.SET_NULL)
    marked_at = models.DateTimeField(auto_now=True)

class GroupMembership(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    group = models.ForeignKey(DanceGroup, on_delete=models.CASCADE)
    starts_on = models.DateField(default=timezone.now)
    ends_on = models.DateField(null=True, blank=True)
    class Meta: unique_together = ("student", "group")

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    event = models.CharField(max_length=80)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    sent = models.BooleanField(default=False)
