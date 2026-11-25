from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *
@admin.register(User)
class StudioUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Роль и телефон", {"fields": ("role","phone")}),)
    list_display = ("username","first_name","last_name","email","role","is_staff")
for model in [Student,Teacher,Direction,Level,StudentLevel,DanceGroup,Hall,Schedule,Lesson,Subscription,Booking,Attendance,GroupMembership,Notification]:
    admin.site.register(model)
