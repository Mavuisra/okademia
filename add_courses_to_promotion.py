#!/usr/bin/env python
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coupon.settings')
django.setup()

from django.contrib.auth.models import User
from belletin.models import Faculty, Department, AcademicYear, Promotion, UE, Professor
from django.utils import timezone
from datetime import date

def add_courses_to_promotion():
    """Ajoute 10 cours (5 par semestre) à une promotion existante ou en crée une nouvelle."""
    
    # 1. Vérifier ou créer l'année académique
    current_year = date.today().year
    academic_year, created = AcademicYear.objects.get_or_create(
        year=date(current_year, 9, 1)  # 1er septembre de l'année courante
    )
    if created:
        print(f"Année académique {academic_year} créée.")
    else:
        print(f"Année académique {academic_year} existante.")
    
    # 2. Vérifier ou créer la faculté et le département
    faculty, created = Faculty.objects.get_or_create(name="Sciences")
    if created:
        print(f"Faculté {faculty.name} créée.")
    
    department, created = Department.objects.get_or_create(
        name="Informatique",
        faculty=faculty
    )
    if created:
        print(f"Département {department.name} créé.")
    
    # 3. Vérifier ou créer la promotion (L1)
    promotion, created = Promotion.objects.get_or_create(
        level='L1',
        department=department,
        academic_year=academic_year
    )
    if created:
        print(f"Promotion {promotion} créée.")
    else:
        print(f"Promotion {promotion} existante.")
    
    # 4. Créer un professeur pour les cours (si aucun n'existe)
    try:
        professor = Professor.objects.first()
        if not professor:
            raise Professor.DoesNotExist
    except Professor.DoesNotExist:
        # Créer un utilisateur pour le professeur
        user, created = User.objects.get_or_create(
            username="prof1",
            defaults={
                'first_name': 'Jean',
                'last_name': 'Dupont',
                'email': 'jean.dupont@example.com',
                'is_staff': True
            }
        )
        if created:
            user.set_password('password123')
            user.save()
            print(f"Utilisateur {user.username} créé.")
        
        professor, created = Professor.objects.get_or_create(
            user=user,
            department=department
        )
        if created:
            print(f"Professeur {professor} créé.")
    
    # 5. Ajouter 5 cours au premier semestre
    semester1_courses = [
        {'code': 'INF101', 'title': 'Introduction à l\'informatique', 'credits': 6},
        {'code': 'INF102', 'title': 'Algorithmique', 'credits': 6},
        {'code': 'MAT101', 'title': 'Mathématiques pour l\'informatique', 'credits': 4},
        {'code': 'PHY101', 'title': 'Physique pour l\'informatique', 'credits': 4},
        {'code': 'ANG101', 'title': 'Anglais technique', 'credits': 2},
    ]
    
    # 6. Ajouter 5 cours au second semestre
    semester2_courses = [
        {'code': 'INF201', 'title': 'Programmation orientée objet', 'credits': 6},
        {'code': 'INF202', 'title': 'Structures de données', 'credits': 6},
        {'code': 'MAT201', 'title': 'Statistiques et probabilités', 'credits': 4},
        {'code': 'RES201', 'title': 'Introduction aux réseaux', 'credits': 4},
        {'code': 'WEB201', 'title': 'Développement Web', 'credits': 2},
    ]
    
    # 7. Créer les UE pour le premier semestre
    for course_data in semester1_courses:
        ue, created = UE.objects.get_or_create(
            code=course_data['code'],
            promotion=promotion,
            semester=1,
            defaults={
                'title': course_data['title'],
                'credits': course_data['credits'],
                'is_group': False
            }
        )
        if created:
            print(f"UE {ue.code} - {ue.title} (S1) créée.")
        else:
            print(f"UE {ue.code} - {ue.title} (S1) existante.")
    
    # 8. Créer les UE pour le second semestre
    for course_data in semester2_courses:
        ue, created = UE.objects.get_or_create(
            code=course_data['code'],
            promotion=promotion,
            semester=2,
            defaults={
                'title': course_data['title'],
                'credits': course_data['credits'],
                'is_group': False
            }
        )
        if created:
            print(f"UE {ue.code} - {ue.title} (S2) créée.")
        else:
            print(f"UE {ue.code} - {ue.title} (S2) existante.")
    
    print("\nTerminé! 10 cours ont été ajoutés à la promotion L1.")
    print(f"Promotion: {promotion}")
    print(f"Année académique: {academic_year}")
    print("Nombre total de crédits: 44")

if __name__ == "__main__":
    add_courses_to_promotion() 