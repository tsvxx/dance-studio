from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Booking, DanceGroup, Lesson, Attendance

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(label="Имя")
    last_name = forms.CharField(label="Фамилия", required=False)
    phone = forms.CharField(label="Телефон", required=False)
    class Meta:
        model = User
        fields = ("username","first_name","last_name","email","phone","password1","password2")

class BookingForm(forms.Form):
    lesson_id = forms.IntegerField(widget=forms.HiddenInput)

class GroupForm(forms.ModelForm):
    class Meta:
        model = DanceGroup
        fields = ["name","direction","level","teacher","capacity","is_active"]

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ["group","hall","starts_at","duration_minutes","status"]
        widgets = {"starts_at": forms.DateTimeInput(attrs={"type":"datetime-local"})}

class AttendanceForm(forms.Form):
    booking_id = forms.IntegerField(widget=forms.HiddenInput)
    was_present = forms.BooleanField(required=False, label="Присутствовал")
