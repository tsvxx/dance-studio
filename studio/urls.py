from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
urlpatterns = [
 path("",views.home,name="home"), path("about/",views.about,name="about"),
 path("directions/",views.directions,name="directions"), path("teachers/",views.teachers,name="teachers"),
 path("schedule/",views.schedule,name="schedule"), path("contacts/",views.contacts,name="contacts"),
 path("register/",views.register,name="register"),
 path("login/",auth_views.LoginView.as_view(template_name="registration/login.html"),name="login"),
 path("logout/",auth_views.LogoutView.as_view(),name="logout"),
 path("dashboard/",views.dashboard,name="dashboard"),
 path("book/<int:lesson_id>/",views.book_lesson,name="book_lesson"),
 path("cancel/<int:booking_id>/",views.cancel_booking,name="cancel_booking"),
 path("availability/<int:lesson_id>/",views.availability,name="availability"),
 path("attendance/<int:lesson_id>/",views.mark_attendance,name="mark_attendance"),
 path("manage/groups/",views.manage_groups,name="manage_groups"),
 path("manage/lessons/",views.manage_lessons,name="manage_lessons"),
 path("manage/groups/<int:group_id>/edit/",views.edit_group,name="edit_group"),
 path("manage/groups/<int:group_id>/delete/",views.delete_group,name="delete_group"),
 path("manage/lessons/<int:lesson_id>/edit/",views.edit_lesson,name="edit_lesson"),
 path("manage/lessons/<int:lesson_id>/delete/",views.delete_lesson,name="delete_lesson"),
 path("stats/",views.stats,name="stats"), path("stats/export/",views.export_csv,name="export_csv"),
]
