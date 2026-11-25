import csv
from datetime import date
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q, F
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.core.mail import send_mail
from .models import *
from .forms import RegisterForm, GroupForm, LessonForm
from .decorators import role_required

def home(request):
    return render(request, "studio/home.html", {
        "directions": Direction.objects.filter(is_active=True)[:5],
        "groups_count": DanceGroup.objects.filter(is_active=True).count(),
        "teachers_count": Teacher.objects.count(),
        "lessons_count": Lesson.objects.filter(status="planned").count(),
        "home_teachers": Teacher.objects.select_related("user").all()[:6],
    })

def about(request): return render(request, "studio/about.html")
def directions(request): return render(request, "studio/directions.html", {"directions": Direction.objects.filter(is_active=True)})

def teachers(request):
    return render(request, "studio/teachers.html", {"teachers": Teacher.objects.select_related("user")})

def schedule(request):
    qs = Lesson.objects.select_related("group__direction","group__level","group__teacher__user","hall").filter(status="planned").order_by("starts_at")
    direction = request.GET.get("direction","")
    level = request.GET.get("level","")
    teacher = request.GET.get("teacher","")
    day = request.GET.get("date","")
    search = request.GET.get("q","")
    if direction: qs = qs.filter(group__direction_id=direction)
    if level: qs = qs.filter(group__level_id=level)
    if teacher: qs = qs.filter(group__teacher_id=teacher)
    if day: qs = qs.filter(starts_at__date=day)
    if search: qs = qs.filter(Q(group__name__icontains=search)|Q(group__direction__name__icontains=search))
    return render(request, "studio/schedule.html", {"lessons": qs[:100], "directions":Direction.objects.all(),"levels":Level.objects.all(),"teachers":Teacher.objects.select_related("user"),"filters":request.GET})

def contacts(request):
    if request.method == "POST":
        name=request.POST.get("name","").strip()
        phone=request.POST.get("phone","").strip()
        message=request.POST.get("message","").strip()
        if name and phone and message:
            messages.success(request,"Спасибо! Мы получили ваше сообщение.")
        else: messages.error(request,"Заполните все поля формы.")
    return render(request,"studio/contacts.html")

def register(request):
    if request.method == "POST":
        form=RegisterForm(request.POST)
        if form.is_valid():
            user=form.save(commit=False); user.role="student"; user.save()
            Student.objects.create(user=user)
            login(request,user)
            messages.success(request,"Регистрация прошла успешно.")
            return redirect("dashboard")
    else: form=RegisterForm()
    return render(request,"registration/register.html",{"form":form})

@login_required
def dashboard(request):
    if request.user.role == "teacher":
        teacher = getattr(request.user,"teacher_profile",None)
        lessons = Lesson.objects.filter(group__teacher=teacher, starts_at__date__gte=date.today()).order_by("starts_at") if teacher else Lesson.objects.none()
        return render(request,"studio/teacher_dashboard.html",{"lessons":lessons})
    if request.user.role == "admin" or request.user.is_superuser:
        return redirect("stats")
    student=getattr(request.user,"student_profile",None)
    if not student: student=Student.objects.create(user=request.user)
    return render(request,"studio/dashboard.html",{"student":student,"subscriptions":student.subscriptions.select_related("direction"),"bookings":student.bookings.select_related("lesson__group").exclude(status="cancelled").order_by("-created_at")[:20]})

@login_required
def book_lesson(request, lesson_id):
    if request.method != "POST": return redirect("schedule")
    if request.user.role != "student": return HttpResponseForbidden("Только ученик может записываться.")
    student=getattr(request.user,"student_profile",None)
    lesson=get_object_or_404(Lesson.objects.select_related("group"),pk=lesson_id,status="planned")
    with transaction.atomic():
        if Booking.objects.filter(student=student,lesson=lesson).exists():
            messages.error(request,"Вы уже записаны на это занятие."); return redirect("schedule")
        sub=Subscription.objects.select_for_update().filter(student=student,direction=lesson.group.direction,status="active",starts_on__lte=date.today(),ends_on__gte=date.today(),visits_used__lt=F("visits_total")).order_by("ends_on").first()
        if not sub:
            messages.error(request,"Нет действующего абонемента на это направление с доступными посещениями."); return redirect("schedule")
        level_ok=StudentLevel.objects.filter(student=student,direction=lesson.group.direction,level=lesson.group.level).exists()
        if not level_ok:
            messages.error(request,"Уровень вашей подготовки не соответствует этой группе."); return redirect("schedule")
        occupied=Booking.objects.filter(lesson=lesson,status="booked").count()
        if occupied >= lesson.group.capacity:
            messages.error(request,"Свободных мест больше нет."); return redirect("schedule")
        booking=Booking.objects.create(student=student,lesson=lesson,subscription=sub)
        sub.visits_used += 1
        if sub.visits_used >= sub.visits_total: sub.status="used"
        sub.save()
        Notification.objects.create(user=request.user,event="booking_created",message=f"Вы записаны: {lesson}")
        send_mail("Запись на занятие",f"Вы записаны на {lesson}.","noreply@dancestudio.local",[request.user.email],fail_silently=True)
    messages.success(request,"Вы успешно записаны!")
    return redirect("dashboard")

@login_required
def cancel_booking(request, booking_id):
    student=getattr(request.user,"student_profile",None)
    booking=get_object_or_404(Booking,pk=booking_id,student=student)
    if request.method=="POST" and booking.status=="booked":
        booking.status="cancelled"; booking.save()
        sub=booking.subscription; sub.visits_used=max(0,sub.visits_used-1)
        if sub.status=="used": sub.status="active"
        sub.save()
        Notification.objects.create(user=request.user,event="booking_cancelled",message=f"Запись отменена: {booking.lesson}")
        messages.success(request,"Запись отменена, посещение возвращено.")
    return redirect("dashboard")

def availability(request, lesson_id):
    lesson=get_object_or_404(Lesson,pk=lesson_id)
    booked=lesson.bookings.filter(status="booked").count()
    return JsonResponse({"capacity":lesson.group.capacity,"booked":booked,"available":max(0,lesson.group.capacity-booked)})

@role_required("teacher")
def mark_attendance(request, lesson_id):
    lesson=get_object_or_404(Lesson,pk=lesson_id)
    teacher=getattr(request.user,"teacher_profile",None)
    if not teacher or lesson.group.teacher_id != teacher.id: return HttpResponseForbidden()
    if request.method=="POST":
        for booking in lesson.bookings.filter(status="booked"):
            present=request.POST.get(f"present_{booking.id}")=="on"
            Attendance.objects.update_or_create(booking=booking,defaults={"was_present":present,"marked_by":teacher})
            booking.status="attended" if present else "missed"; booking.save()
        lesson.status="done"; lesson.save()
        messages.success(request,"Посещаемость сохранена.")
        return redirect("dashboard")
    return render(request,"studio/attendance.html",{"lesson":lesson,"bookings":lesson.bookings.filter(status="booked").select_related("student__user")})

@role_required("admin")
def manage_groups(request):
    if request.method=="POST":
        form=GroupForm(request.POST)
        if form.is_valid(): form.save(); messages.success(request,"Группа создана."); return redirect("manage_groups")
    else: form=GroupForm()
    return render(request,"studio/manage_groups.html",{"form":form,"groups":DanceGroup.objects.select_related("direction","level","teacher__user")})

@role_required("admin")
def manage_lessons(request):
    if request.method=="POST":
        form=LessonForm(request.POST)
        if form.is_valid(): form.save(); messages.success(request,"Занятие добавлено."); return redirect("manage_lessons")
    else: form=LessonForm()
    return render(request,"studio/manage_lessons.html",{"form":form,"lessons":Lesson.objects.order_by("-starts_at")[:50]})

@role_required("admin")
def stats(request):
    month=request.GET.get("month",timezone.localdate().strftime("%Y-%m"))
    try: year,mon=map(int,month.split("-"))
    except: year,mon=timezone.localdate().year,timezone.localdate().month
    groups=[]
    for group in DanceGroup.objects.select_related("direction","level"):
        lessons=Lesson.objects.filter(group=group,status="done",starts_at__year=year,starts_at__month=mon)
        lesson_count=lessons.count()
        active_members=GroupMembership.objects.filter(group=group,starts_on__lte=date(year,mon,1)).filter(Q(ends_on__isnull=True)|Q(ends_on__gte=date(year,mon,1))).count()
        possible=lesson_count*active_members
        actual=Attendance.objects.filter(booking__lesson__in=lessons,was_present=True).count()
        percent=round(actual/possible*100,1) if possible else None
        groups.append({"group":group,"lessons":lesson_count,"members":active_members,"actual":actual,"percent":percent})
    return render(request,"studio/stats.html",{"groups":groups,"month":month})

@role_required("admin")
def export_csv(request):
    response=HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"]='attachment; filename="attendance_report.csv"'
    response.write("\\ufeff")
    writer=csv.writer(response,delimiter=";")
    writer.writerow(["Группа","Направление","Уровень","Занятий","Участников","Посещений","Посещаемость, %"])
    for group in DanceGroup.objects.select_related("direction","level"):
        lessons=Lesson.objects.filter(group=group,status="done")
        n=lessons.count(); members=GroupMembership.objects.filter(group=group).count()
        actual=Attendance.objects.filter(booking__lesson__in=lessons,was_present=True).count()
        possible=n*members
        writer.writerow([group.name,group.direction.name,group.level.name,n,members,actual,round(actual/possible*100,1) if possible else "нет данных"])
    return response


@role_required("admin")
def edit_group(request, group_id):
    group=get_object_or_404(DanceGroup,pk=group_id)
    if request.method=="POST":
        form=GroupForm(request.POST,instance=group)
        if form.is_valid(): form.save(); messages.success(request,"Изменения группы сохранены."); return redirect("manage_groups")
    else: form=GroupForm(instance=group)
    return render(request,"studio/edit_item.html",{"form":form,"heading":"Изменить группу","back_url":"manage_groups"})

@role_required("admin")
def delete_group(request, group_id):
    group=get_object_or_404(DanceGroup,pk=group_id)
    if request.method=="POST":
        group.delete(); messages.success(request,"Группа удалена."); return redirect("manage_groups")
    return render(request,"studio/confirm_delete.html",{"object":group,"back_url":"manage_groups"})

@role_required("admin")
def edit_lesson(request, lesson_id):
    lesson=get_object_or_404(Lesson,pk=lesson_id)
    if request.method=="POST":
        form=LessonForm(request.POST,instance=lesson)
        if form.is_valid(): form.save(); messages.success(request,"Изменения занятия сохранены."); return redirect("manage_lessons")
    else: form=LessonForm(instance=lesson)
    return render(request,"studio/edit_item.html",{"form":form,"heading":"Изменить занятие","back_url":"manage_lessons"})

@role_required("admin")
def delete_lesson(request, lesson_id):
    lesson=get_object_or_404(Lesson,pk=lesson_id)
    if request.method=="POST":
        lesson.delete(); messages.success(request,"Занятие удалено."); return redirect("manage_lessons")
    return render(request,"studio/confirm_delete.html",{"object":lesson,"back_url":"manage_lessons"})
