from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, time
from studio.models import *

class Command(BaseCommand):
    help = "Создаёт демонстрационные данные для Dance Studio"
    def handle(self,*args,**kwargs):
        admin,created=User.objects.get_or_create(username="admin",defaults={"email":"admin@example.com","role":"admin","is_staff":True,"is_superuser":True,"first_name":"Администратор"})
        if created: admin.set_password("DanceAdmin123!"); admin.save()
        teacher_user,_=User.objects.get_or_create(username="teacher",defaults={"email":"teacher@example.com","role":"teacher","first_name":"Анна","last_name":"Петрова"})
        teacher_user.set_password("DanceTeacher123!"); teacher_user.save()
        teacher,_=Teacher.objects.get_or_create(user=teacher_user,defaults={"bio":"Профессиональный педагог с опытом более 8 лет."})
        # Дополнительные демонстрационные преподаватели для наполнения страницы команды.
        extra_teachers = [
            ("teacher_elena", "Елена", "Соколова", "Преподаватель классического танца. Помогает развивать осанку, координацию и чистоту движений."),
            ("teacher_maria", "Мария", "Орлова", "Педагог современных направлений. Работает над пластикой, музыкальностью и выразительностью."),
            ("teacher_alex", "Александра", "Миронова", "Преподаватель уличных стилей. На занятиях соединяет энергию, ритм и индивидуальность."),
            ("teacher_daria", "Дарья", "Волкова", "Педагог направления High Heels. Помогает обрести уверенность, баланс и сценическую подачу."),
            ("teacher_natalia", "Наталья", "Крылова", "Преподаватель Dance Fitness. Сочетает танцевальную энергетику и функциональную нагрузку."),
            ("teacher_irina", "Ирина", "Лебедева", "Педагог contemporary. Работает над пластикой, импровизацией и выразительностью движения."),
            ("teacher_sofia", "София", "Романова", "Преподаватель jazz-funk и сценической хореографии. Развивает артистизм и чувство ритма."),
        ]
        for username, first, last, bio in extra_teachers:
            u, _ = User.objects.get_or_create(username=username, defaults={"email": f"{username}@example.com", "role": "teacher", "first_name": first, "last_name": last})
            u.role = "teacher"
            u.save()
            Teacher.objects.get_or_create(user=u, defaults={"bio": bio})
        student_user,_=User.objects.get_or_create(username="student",defaults={"email":"student@example.com","role":"student","first_name":"Мария","last_name":"Иванова"})
        student_user.set_password("DanceStudent123!"); student_user.save()
        student,_=Student.objects.get_or_create(user=student_user)
        dirs=[]
        for name,desc in [("Балет","Классическая техника, пластика и осанка."),("Хип-хоп","Энергия улиц, ритм и свобода."),("Контемпорари","Современный танец и выразительность."),("High Heels","Женственная хореография и уверенность."),("Dance Fitness","Танец и фитнес в одном занятии.")]:
            d,_=Direction.objects.get_or_create(name=name,defaults={"description":desc}); dirs.append(d)
        levels=[]
        for i,n in enumerate(["Начинающий","Средний","Продвинутый"],1):
            l,_=Level.objects.get_or_create(name=n,defaults={"order":i}); levels.append(l)
        hall,_=Hall.objects.get_or_create(name="Большой зал",defaults={"capacity":20})
        for i,d in enumerate(dirs):
            group,_=DanceGroup.objects.get_or_create(name=f"{d.name} — группа {i+1}",defaults={"direction":d,"level":levels[0],"teacher":teacher,"capacity":12})
            GroupMembership.objects.get_or_create(student=student,group=group)
            if i==0:
                StudentLevel.objects.get_or_create(student=student,direction=d,defaults={"level":levels[0],"approved_by":teacher})
                Subscription.objects.get_or_create(student=student,direction=d,defaults={"starts_on":timezone.localdate()-timedelta(days=5),"ends_on":timezone.localdate()+timedelta(days=90),"visits_total":12})
            for j in range(6):
                dt=timezone.now()+timedelta(days=j+1,hours=1)
                Lesson.objects.get_or_create(group=group,starts_at=dt,defaults={"hall":hall,"duration_minutes":60})
        # Ещё два учебных профиля: вместе с основным учеником создают не менее 10 тестовых записей.
        demo_students=[student]
        for username,first in [("student2","Елена"),("student3","Ольга")]:
            u,_=User.objects.get_or_create(username=username,defaults={"email":f"{username}@example.com","role":"student","first_name":first})
            u.set_password("DanceStudent123!"); u.save()
            st,_=Student.objects.get_or_create(user=u); demo_students.append(st)
            GroupMembership.objects.get_or_create(student=st,group=DanceGroup.objects.filter(direction=dirs[0]).first())
            StudentLevel.objects.get_or_create(student=st,direction=dirs[0],defaults={"level":levels[0],"approved_by":teacher})
            Subscription.objects.get_or_create(student=st,direction=dirs[0],defaults={"starts_on":timezone.localdate()-timedelta(days=5),"ends_on":timezone.localdate()+timedelta(days=90),"visits_total":12})
        ballet_group=DanceGroup.objects.filter(direction=dirs[0]).first()
        ballet_lessons=list(Lesson.objects.filter(group=ballet_group).order_by("starts_at")[:6])
        for st in demo_students:
            sub=Subscription.objects.get(student=st,direction=dirs[0])
            for lesson in ballet_lessons[:4]:
                Booking.objects.get_or_create(student=st,lesson=lesson,defaults={"subscription":sub})
            sub.visits_used=Booking.objects.filter(student=st,subscription=sub,status="booked").count(); sub.save()
        self.stdout.write(self.style.SUCCESS("Демо-данные созданы: 30 занятий и не менее 10 записей. Логины: admin / teacher / student. Пароли: DanceAdmin123! / DanceTeacher123! / DanceStudent123!"))
