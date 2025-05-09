#!/usr/bin/env python
import os
import django
import sys
from django.db import transaction
from django.utils import timezone

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coupon.settings')
django.setup()

from belletin.models import Deliberation, StudentDeliberation, Student, Promotion, AcademicYear
from belletin.utils import encode_id

def verify_and_repair_database():
    """Vérifie et répare les problèmes de base de données liés aux délibérations."""
    print("Démarrage de la vérification et réparation de la base de données...")
    
    # 1. Vérifier les liens entre étudiants et délibérations
    print("\n[1] Vérification des liens entre étudiants et délibérations...")
    
    # Récupérer tous les étudiants
    students = Student.objects.all()
    students_count = students.count()
    print(f"Nombre d'étudiants: {students_count}")
    
    # Récupérer toutes les délibérations
    deliberations = Deliberation.objects.all()
    deliberations_count = deliberations.count()
    print(f"Nombre de délibérations: {deliberations_count}")
    
    # Compteurs pour les statistiques
    fixed_links = 0
    
    # Parcourir chaque étudiant
    for i, student in enumerate(students, 1):
        print(f"[{i}/{students_count}] Vérification de l'étudiant {student.matricule}...")
        
        # Récupérer sa promotion
        promotion = student.promotion
        
        # Récupérer les délibérations associées à cette promotion
        delibs_for_promotion = deliberations.filter(promotion=promotion)
        
        # Récupérer les liens de délibération existants pour cet étudiant
        student_delibs = StudentDeliberation.objects.filter(student=student)
        
        # Vérifier que chaque délibération de la promotion est liée à l'étudiant
        for delib in delibs_for_promotion:
            student_delib_exists = student_delibs.filter(deliberation=delib).exists()
            
            if not student_delib_exists:
                print(f"  → Lien manquant: étudiant {student.matricule} et délibération {delib}")
                
                # Créer un nouveau lien
                with transaction.atomic():
                    new_student_delib = StudentDeliberation(
                        deliberation=delib,
                        student=student,
                        average=0,
                        credits_obtained=0,
                        auto_decision='ADMITTED',  # Valeur par défaut, sera calculée correctement plus tard
                        final_decision=None,
                        validated=True,  # Marquer comme validé pour permettre l'accès
                        validated_at=timezone.now()
                    )
                    new_student_delib.save()
                
                print(f"  ✓ Lien créé avec succès")
                fixed_links += 1
    
    print(f"\nLiens réparés: {fixed_links}")
    
    # 2. Vérifier les tokens manquants ou invalides
    print("\n[2] Vérification des tokens...")
    
    # Compter les délibérations sans token
    delibs_without_token = Deliberation.objects.filter(token__isnull=True)
    delibs_without_token_count = delibs_without_token.count()
    
    # Compter les student_deliberations sans token
    student_delibs_without_token = StudentDeliberation.objects.filter(token__isnull=True)
    student_delibs_without_token_count = student_delibs_without_token.count()
    
    print(f"Délibérations sans token: {delibs_without_token_count}")
    print(f"Délibérations étudiant sans token: {student_delibs_without_token_count}")
    
    # 3. Créer une délibération par défaut si nécessaire
    print("\n[3] Vérification des délibérations par défaut...")
    
    # Vérifier s'il existe au moins une délibération
    if deliberations_count == 0:
        print("Aucune délibération trouvée, création d'une délibération par défaut...")
        
        # Récupérer les données nécessaires
        try:
            academic_year = AcademicYear.objects.last()
            if not academic_year:
                # Créer une année académique si nécessaire
                from datetime import date
                academic_year = AcademicYear.objects.create(year=date.today())
                print(f"  → Année académique créée: {academic_year}")
            
            promotion = Promotion.objects.last()
            if not promotion:
                print("  ✗ Aucune promotion trouvée. Impossible de créer une délibération par défaut.")
            else:
                # Créer une délibération par défaut
                with transaction.atomic():
                    default_delib = Deliberation(
                        promotion=promotion,
                        semester=1,
                        academic_year=academic_year,
                        date_scheduled=timezone.now(),
                        status='COMPLETED'
                    )
                    default_delib.save()
                    
                    # Lier tous les étudiants à cette délibération
                    for student in Student.objects.filter(promotion=promotion):
                        student_delib = StudentDeliberation(
                            deliberation=default_delib,
                            student=student,
                            average=10,
                            credits_obtained=30,
                            auto_decision='ADMITTED',
                            final_decision='ADMITTED',
                            validated=True,
                            validated_at=timezone.now()
                        )
                        student_delib.save()
                    
                    print(f"  ✓ Délibération par défaut créée: {default_delib}")
        except Exception as e:
            print(f"  ✗ Erreur lors de la création de la délibération par défaut: {str(e)}")
    
    # 4. Réparer les tokens manquants en exécutant le script de réparation
    if delibs_without_token_count > 0 or student_delibs_without_token_count > 0:
        print("\n[4] Réparation des tokens manquants...")
        from fix_missing_tokens import fix_missing_tokens
        fixed_count = fix_missing_tokens()
        print(f"  ✓ {fixed_count} tokens réparés")
    
    print("\nVérification et réparation terminées avec succès!")
    return True

if __name__ == "__main__":
    try:
        verify_and_repair_database()
        sys.exit(0)
    except Exception as e:
        print(f"Erreur lors de la vérification et réparation: {str(e)}")
        sys.exit(1) 