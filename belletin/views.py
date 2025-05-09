from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login
from .models import (
    Student, Grade, UE, AnnualReport, Faculty, 
    Department, Promotion, AcademicYear, Course, GradeComponent,
    Professor, GradeModificationLog, JuryMember, Deliberation,
    StudentDeliberation, DeliberationChangeLog, DeliberationMember,
    PromotionHistory, OfflineQueue
)
from .forms import (
    StudentForm, GradeForm, UEForm, FacultyForm,
    DepartmentForm, PromotionForm, QuickGradeForm,
    DeliberationCreateForm, DeliberationFilterForm,
    StudentDeliberationDecisionForm, StudentDeliberationBulkForm,
    DeliberationChangeLogForm
)
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Avg, Sum, F, Case, When, Value, IntegerField
from django.urls import reverse
from django.db import transaction
import json
import csv
from django.template.loader import render_to_string
import tempfile
import os
import datetime
from .offline import OfflineMixin  # Ajouter cette importation

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Vérifier si l'utilisateur est un professeur
            try:
                professor = user.professor
                return redirect('belletin:professor_dashboard')
            except Professor.DoesNotExist:
                pass
            
            # Vérifier si l'utilisateur est un étudiant
            try:
                student = user.student
                # TODO: Ajouter une redirection vers le dashboard étudiant
                return redirect('belletin:dashboard')
            except Student.DoesNotExist:
                pass
            
            # Si l'utilisateur n'est ni professeur ni étudiant
            if user.is_staff:
                return redirect('belletin:dashboard')
            else:
                return redirect('belletin:dashboard')
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
    
    return render(request, 'auth/login.html')

@login_required
def dashboard(request):
    # Vérifier si l'utilisateur est un professeur
    try:
        professor = request.user.professor
        return redirect('belletin:professor_dashboard')
    except Professor.DoesNotExist:
        pass
    
    # Vérifier si l'utilisateur est un étudiant
    try:
        student = request.user.student
        # TODO: Ajouter une vue pour le dashboard étudiant
        pass
    except Student.DoesNotExist:
        pass
    
    # Si l'utilisateur n'est ni professeur ni étudiant, afficher le dashboard par défaut
    context = {
        'students_count': Student.objects.count(),
        'faculties_count': Faculty.objects.count(),
        'departments_count': Department.objects.count(),
        'current_year': AcademicYear.objects.last()
    }
    return render(request, 'belletin/dashboard.html', context)

# Faculty views
@login_required
def faculty_list(request):
    faculties = Faculty.objects.all()
    return render(request, 'belletin/faculty/list.html', {'faculties': faculties})

@login_required
def faculty_create(request):
    if request.method == 'POST':
        form = FacultyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Faculté créée avec succès.')
            return redirect('faculty_list')
    else:
        form = FacultyForm()
    return render(request, 'belletin/faculty/form.html', {'form': form})

# Department views
@login_required
def department_list(request):
    departments = Department.objects.all()
    return render(request, 'belletin/department/list.html', {'departments': departments})

@login_required
def department_create(request):
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Département créé avec succès.')
            return redirect('department_list')
    else:
        form = DepartmentForm()
    return render(request, 'belletin/department/form.html', {'form': form})

# Student views
@login_required
def student_list(request):
    students = Student.objects.all()
    return render(request, 'belletin/student/list.html', {'students': students})

@login_required
def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk)
    grades = Grade.objects.filter(student=student)
    return render(request, 'belletin/student/detail.html', {
        'student': student,
        'grades': grades
    })

@login_required
def student_create(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Étudiant créé avec succès.')
            return redirect('student_list')
    else:
        form = StudentForm()
    return render(request, 'belletin/student/form.html', {'form': form})

# Grade views
@login_required
def grade_create(request, student_id, ue_id):
    student = get_object_or_404(Student, pk=student_id)
    ue = get_object_or_404(UE, pk=ue_id)
    
    if request.method == 'POST':
        form = GradeForm(request.POST)
        if form.is_valid():
            grade = form.save(commit=False)
            grade.student = student
            grade.ue = ue
            grade.save()
            messages.success(request, 'Note enregistrée avec succès.')
            return redirect('student_detail', pk=student_id)
    else:
        form = GradeForm()
    
    return render(request, 'belletin/grade/form.html', {
        'form': form,
        'student': student,
        'ue': ue
    })

# UE views
@login_required
def ue_list(request):
    ues = UE.objects.all()
    return render(request, 'belletin/ue/list.html', {'ues': ues})

@login_required
def ue_create(request):
    if request.method == 'POST':
        form = UEForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'UE créée avec succès.')
            return redirect('ue_list')
    else:
        form = UEForm()
    return render(request, 'belletin/ue/form.html', {'form': form})

# Report generation
@login_required
def generate_annual_report(request, student_id, year_id):
    student = get_object_or_404(Student, pk=student_id)
    academic_year = get_object_or_404(AcademicYear, pk=year_id)
    
    # Logique pour calculer les moyennes et crédits
    grades = Grade.objects.filter(
        student=student,
        ue__promotion__academic_year=academic_year
    )
    
    total_credits = sum(grade.ue.credits for grade in grades if grade.cc is not None and grade.mc is not None)
    
    # Calcul de la moyenne annuelle (à adapter selon vos besoins)
    total_points = sum(
        ((grade.cc + grade.mc) / 2) * grade.ue.credits 
        for grade in grades 
        if grade.cc is not None and grade.mc is not None
    )
    
    if total_credits > 0:
        annual_average = total_points / total_credits
    else:
        annual_average = 0
    
    # Détermination de l'appréciation
    if annual_average >= 16:
        appreciation = "Très Bien"
    elif annual_average >= 14:
        appreciation = "Bien"
    elif annual_average >= 12:
        appreciation = "Assez Bien"
    elif annual_average >= 10:
        appreciation = "Passable"
    else:
        appreciation = "Insuffisant"
    
    # Création ou mise à jour du rapport
    report, created = AnnualReport.objects.update_or_create(
        student=student,
        academic_year=academic_year,
        defaults={
            'total_credits': total_credits,
            'annual_average': annual_average,
            'appreciation': appreciation
        }
    )
    
    messages.success(request, 'Rapport annuel généré avec succès.')
    return redirect('student_detail', pk=student_id)

@login_required
def professor_dashboard(request):
    try:
        professor = request.user.professor
    except Professor.DoesNotExist:
        messages.error(request, "Accès non autorisé. Vous n'êtes pas un professeur.")
        return redirect('belletin:dashboard')
    
    # Synchroniser les notes en arrière-plan
    from .utils import synchronize_all_grades
    try:
        result = synchronize_all_grades()
        if result['updated'] > 0:
            messages.success(request, f"{result['updated']} notes ont été synchronisées avec succès.")
    except Exception as e:
        # Ne pas afficher d'erreur à l'utilisateur, juste journaliser
        print(f"Erreur lors de la synchronisation des notes: {str(e)}")
    
    # Date actuelle pour le template
    from datetime import datetime
    current_date = datetime.now().strftime("%d %B %Y")
    
    # Récupérer les cours actifs du professeur
    current_year = AcademicYear.objects.last()
    courses = Course.objects.filter(
        professor=professor,
        academic_year=current_year,
        is_active=True
    )
    
    # Récupérer les UEs associées aux cours
    teaching_units = []
    course_mapping = {}  # Pour associer les UEs à leurs cours
    
    for course in courses:
        try:
            # Vérifier si la relation est directe ou indirecte
            if hasattr(course, 'ue'):
                ue = course.ue
            else:
                # Si la relation est inversée
                continue  # On passe au cours suivant si pas de relation
                
            # Calculer le taux de complétion (pourcentage d'étudiants notés)
            try:
                total_students = Student.objects.filter(promotion=ue.promotion).count()
                graded_students = Grade.objects.filter(ue=ue).count()
                completion_rate = 0
                if total_students > 0:
                    completion_rate = int((graded_students / total_students) * 100)
                
                # Obtenir l'affichage du niveau
                try:
                    level_display = ue.get_level_display()
                except:
                    level_display = str(ue.level)
                
                # Vérification si l'UE est déjà dans la liste (éviter les doublons)
                if not any(item['id'] == ue.id for item in teaching_units):
                    # Enregistrer l'association UE -> Cours pour le lien quick_grade
                    course_mapping[ue.id] = course.id
                    
                    # Ajouter les données de l'UE au tableau
                    teaching_units.append({
                        'id': ue.id,
                        'course_id': course.id,  # Ajout de l'ID du cours pour le lien quick_grade
                        'name': ue.name,
                        'department': getattr(ue, 'department', {'name': 'Non spécifié'}),
                        'level_display': level_display,
                        'completion_rate': completion_rate
                    })
                    print(f"UE ajoutée: {ue.name} (ID: {ue.id}, Course ID: {course.id})")
            except Exception as e:
                print(f"Erreur lors du calcul des statistiques pour l'UE {ue.id}: {str(e)}")
                
        except Exception as e:
            print(f"Erreur lors du traitement du cours {course.id}: {str(e)}")
            continue
    
    print(f"Nombre d'UEs trouvées: {len(teaching_units)}")
    
    # Calculer les statistiques
    total_students = 0
    pending_grades = 0
    
    for course in courses:
        try:
            if hasattr(course, 'ue'):
                ue = course.ue
                try:
                    students_in_course = Student.objects.filter(promotion=ue.promotion).count()
                    graded_students = Grade.objects.filter(ue=ue).count()
                    total_students += students_in_course
                    pending_grades += max(0, students_in_course - graded_students)
                except Exception as e:
                    print(f"Erreur dans le calcul des statistiques pour le cours {course.id}: {str(e)}")
        except Exception as e:
            print(f"Erreur de récupération de l'UE pour le cours {course.id}: {str(e)}")
    
    stats = {
        'ue_count': courses.count(),
        'total_students': total_students,
        'pending_grades': pending_grades,
        'upcoming_deadlines': None  # À implémenter si nécessaire
    }
    
    # Calculer la distribution des notes pour le graphique
    grade_distribution = [0, 0, 0, 0, 0, 0]  # Excellent, Très bien, Bien, Assez bien, Passable, Échec
    
    try:
        # Récupérer les UEs des cours du professeur
        course_ues = [course.ue.id for course in courses if hasattr(course, 'ue')]
        
        # Récupérer les notes pour ces UEs
        all_grades = Grade.objects.filter(ue_id__in=course_ues)
        
        for grade in all_grades:
            try:
                final_grade = (grade.cc + grade.mc) / 2  # Calcul de la moyenne finale
                if final_grade >= 16:
                    grade_distribution[0] += 1  # Excellent
                elif final_grade >= 14:
                    grade_distribution[1] += 1  # Très bien
                elif final_grade >= 12:
                    grade_distribution[2] += 1  # Bien
                elif final_grade >= 11:
                    grade_distribution[3] += 1  # Assez bien
                elif final_grade >= 10:
                    grade_distribution[4] += 1  # Passable
                else:
                    grade_distribution[5] += 1  # Échec
            except Exception as e:
                print(f"Erreur lors du traitement de la note {grade.id}: {str(e)}")
    except Exception as e:
        print(f"Erreur lors du calcul de la distribution des notes: {str(e)}")
    
    context = {
        'professor': professor,
        'courses': courses,
        'current_date': current_date,
        'stats': stats,
        'teaching_units': teaching_units,
        'grade_distribution': grade_distribution
    }
    
    return render(request, 'professor/dashboard.html', context)

@login_required
def quick_grade(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Vérifier que l'utilisateur est bien le professeur du cours
    if request.user.professor != course.professor:
        messages.error(request, "Vous n'êtes pas autorisé à noter ce cours.")
        return redirect('belletin:professor_dashboard')
    
    # Récupérer tous les étudiants de la promotion
    students = Student.objects.filter(
        promotion=course.ue.promotion
    ).select_related('user').order_by('matricule')
    
    # Traiter la soumission du formulaire
    if request.method == 'POST':
        # Vérifier si la requête est en mode hors ligne
        is_offline = request.POST.get('offline_mode') == 'true' or request.headers.get('X-Offline-Mode') == 'true'
        
        action = request.POST.get('action', 'create')
        
        # Création ou mise à jour de note
        if action in ['create', 'update']:
            student_id = request.POST.get('student')
            tp = request.POST.get('tp')
            interrogation = request.POST.get('interrogation')
            examen = request.POST.get('examen')
            grade_id = request.POST.get('grade_id')
            
            if student_id and tp and interrogation and examen:
                # Si mode hors ligne, enregistrer l'opération pour synchronisation future
                if is_offline:
                    # Construire les données de l'opération
                    operation_data = {
                        'course_id': course_id,
                        'student_id': student_id,
                        'tp': tp,
                        'interrogation': interrogation,
                        'examen': examen,
                        'action': action,
                        'grade_id': grade_id
                    }
                    
                    # Créer une entrée dans la file d'attente hors ligne
                    queue_item = OfflineQueue.objects.create(
                        operation_type='UPDATE' if action == 'update' else 'CREATE',
                        model_name='GradeComponent',
                        object_id=student_id,
                        user=request.user,
                        data=operation_data
                    )
                    
                    messages.success(request, f"Opération enregistrée en mode hors ligne. Elle sera synchronisée lorsque vous serez connecté à Internet.")
                    return redirect('belletin:quick_grade', course_id=course_id)
                
                # Mode normal (en ligne)
                student = get_object_or_404(Student, id=student_id)
                
                # Créer ou mettre à jour les composantes de note
                components = {
                    'TP': float(tp),
                    'INTERROGATION': float(interrogation),
                    'EXAMEN': float(examen)
                }
                
                for component_type, score in components.items():
                    GradeComponent.objects.update_or_create(
                        course=course,
                        student=student,
                        type=component_type,
                        defaults={'score': score}
                    )
                
                # Synchroniser avec le modèle Grade
                # Calculer la note de contrôle continu (cc) et la note d'examen (mc)
                cc = components['TP'] + components['INTERROGATION']  # TP (5) + Interrogation (5) = 10
                mc = components['EXAMEN'] * 2  # Examen (10) converti en note sur 20
                
                # Créer ou mettre à jour l'enregistrement Grade
                grade, created = Grade.objects.update_or_create(
                    student=student,
                    ue=course.ue,
                    defaults={
                        'cc': cc,
                        'mc': mc
                    }
                )
                
                if action == 'create':
                    messages.success(request, f"Notes enregistrées pour {student.user.get_full_name()}")
                else:
                    messages.success(request, f"Notes modifiées pour {student.user.get_full_name()}")
                return redirect('belletin:quick_grade', course_id=course_id)
            else:
                messages.error(request, "Veuillez remplir tous les champs")
        
        # Suppression de note
        elif action == 'delete':
            student_id = request.POST.get('student_id')
            if student_id:
                # Si mode hors ligne, enregistrer l'opération pour synchronisation future
                if is_offline:
                    # Construire les données de l'opération
                    operation_data = {
                        'course_id': course_id,
                        'student_id': student_id,
                        'action': 'delete'
                    }
                    
                    # Créer une entrée dans la file d'attente hors ligne
                    queue_item = OfflineQueue.objects.create(
                        operation_type='DELETE',
                        model_name='GradeComponent',
                        object_id=student_id,
                        user=request.user,
                        data=operation_data
                    )
                    
                    messages.success(request, f"Suppression enregistrée en mode hors ligne. Elle sera synchronisée lorsque vous serez connecté à Internet.")
                    return redirect('belletin:quick_grade', course_id=course_id)
                
                # Mode normal (en ligne)
                student = get_object_or_404(Student, id=student_id)
                deleted, _ = GradeComponent.objects.filter(
                    course=course,
                    student=student
                ).delete()
                
                # Supprimer également l'enregistrement Grade correspondant
                Grade.objects.filter(student=student, ue=course.ue).delete()
                
                if deleted:
                    messages.success(request, f"Notes supprimées pour {student.user.get_full_name()}")
                else:
                    messages.warning(request, "Aucune note à supprimer")
                return redirect('belletin:quick_grade', course_id=course_id)
            else:
                messages.error(request, "Étudiant non spécifié")
    
    # Récupérer les notes existantes
    existing_grades = GradeComponent.objects.filter(
        course=course
    ).select_related('student', 'student__user').order_by('student__matricule', 'type')
    
    # Regrouper les notes par étudiant
    students_grades = {}
    for grade in existing_grades:
        if grade.student_id not in students_grades:
            students_grades[grade.student_id] = {
                'student': grade.student,
                'grades': {'TP': None, 'INTERROGATION': None, 'EXAMEN': None}
            }
        students_grades[grade.student_id]['grades'][grade.type] = grade.score
    
    # Obtenir l'étudiant à modifier si spécifié
    edit_student_id = request.GET.get('edit')
    edit_student_data = None
    if edit_student_id and edit_student_id.isdigit():
        if int(edit_student_id) in students_grades:
            edit_student_data = students_grades[int(edit_student_id)]
    
    context = {
        'course': course,
        'students': students,
        'students_grades': students_grades.values(),
        'edit_student_data': edit_student_data,
        'offline_supported': True  # Indiquer que cette page supporte le mode hors ligne
    }
    
    return render(request, 'professor/quick_grade.html', context)

@login_required
def grade_detail(request, course_id, student_id):
    """Vue détaillée des notes d'un étudiant pour un cours"""
    course = get_object_or_404(Course, id=course_id)
    student = get_object_or_404(Student, id=student_id)
    
    # Vérifier que l'utilisateur est bien le professeur du cours
    if request.user.professor != course.professor:
        messages.error(request, "Accès non autorisé.")
        return redirect('belletin:professor_dashboard')
    
    # Récupérer les notes de l'étudiant
    grade_components = GradeComponent.objects.filter(
        course=course,
        student=student
    ).order_by('type')
    
    # Calculer la note totale
    total_score = 0
    has_all_components = True
    components = {'TP': None, 'INTERROGATION': None, 'EXAMEN': None}
    
    for component in grade_components:
        components[component.type] = component.score
        if component.score is not None:
            total_score += component.score
        else:
            has_all_components = False
    
    # Synchroniser avec le modèle Grade si toutes les composantes sont présentes
    if has_all_components:
        cc = components['TP'] + components['INTERROGATION']  # TP (5) + Interrogation (5) = 10
        mc = components['EXAMEN'] * 2  # Examen (10) converti en note sur 20
        
        Grade.objects.update_or_create(
            student=student,
            ue=course.ue,
            defaults={
                'cc': cc,
                'mc': mc
            }
        )
    
    # Récupérer l'historique des modifications
    modification_logs = GradeModificationLog.objects.filter(
        component__course=course,
        component__student=student
    ).order_by('-modified_at')[:10]
    
    context = {
        'course': course,
        'student': student,
        'grade_components': grade_components,
        'total_score': total_score if has_all_components else None,
        'modification_logs': modification_logs
    }
    
    return render(request, 'professor/grade_detail.html', context)

@login_required
def professor_grades(request):
    try:
        professor = request.user.professor
    except Professor.DoesNotExist:
        messages.error(request, "Accès non autorisé. Vous n'êtes pas un professeur.")
        return redirect('belletin:dashboard')
    
    # Récupérer les cours actifs du professeur avec les statistiques
    current_year = AcademicYear.objects.last()
    courses = Course.objects.filter(
        professor=professor,
        academic_year=current_year,
        is_active=True
    )
    
    # Enrichir les cours avec des statistiques
    for course in courses:
        # Nombre d'étudiants dans le cours
        course.students_count = Student.objects.filter(
            promotion=course.ue.promotion
        ).count()
        
        # Taux de complétion des notes
        total_components = course.students_count * 3  # TP, Interrogation, Examen
        completed_components = GradeComponent.objects.filter(
            course=course,
            score__isnull=False
        ).count()
        
        course.completion_rate = round((completed_components / total_components * 100) if total_components > 0 else 0)
    
    context = {
        'professor': professor,
        'courses': courses,
        'current_year': current_year,
    }
    
    return render(request, 'professor/grades.html', context)

@login_required
def api_search_students(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Vérifier que l'utilisateur est bien le professeur du cours
    if request.user.professor != course.professor:
        return JsonResponse({'error': 'Non autorisé'}, status=403)
    
    # Récupérer le terme de recherche
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse({'students': []})
    
    # Rechercher les étudiants de la promotion du cours
    students = Student.objects.filter(
        promotion=course.ue.promotion
    ).filter(
        Q(user__first_name__icontains=query) |
        Q(user__last_name__icontains=query) |
        Q(matricule__icontains=query)
    )[:10]
    
    # Formater les résultats
    results = [{
        'id': student.id,
        'matricule': student.matricule,
        'full_name': student.user.get_full_name()
    } for student in students]
    
    return JsonResponse({'students': results})

# Vues pour le jury

@login_required
def jury_dashboard(request):
    """Tableau de bord pour les membres du jury"""
    # Vérifier si l'utilisateur est un membre du jury
    try:
        jury_member = request.user.jurymember
    except JuryMember.DoesNotExist:
        messages.error(request, "Accès non autorisé. Vous n'êtes pas un membre du jury.")
        return redirect('belletin:dashboard')
    
    # Obtenir les promotions auxquelles le membre du jury appartient
    promotions = jury_member.promotions.all()
    
    # Obtenir les délibérations associées aux promotions
    deliberations = Deliberation.objects.filter(
        promotion__in=promotions,
        status__in=['PENDING', 'IN_PROGRESS']
    ).order_by('date_scheduled')
    
    # Obtenir les statistiques générales
    stats = {}
    
    # Nombre total d'étudiants sous la responsabilité du jury
    stats['total_students'] = Student.objects.filter(
        promotion__in=promotions
    ).count()
    
    # Nombre de délibérations en attente
    stats['pending_deliberations'] = deliberations.filter(status='PENDING').count()
    
    # Nombre de délibérations en cours
    stats['in_progress_deliberations'] = deliberations.filter(status='IN_PROGRESS').count()
    
    # Délibérations récentes terminées - accessible à tous les membres du jury
    recent_completed = Deliberation.objects.filter(
        promotion__in=promotions,
        status='COMPLETED'
    ).order_by('-date_completed')[:5]
    
    context = {
        'jury_member': jury_member,
        'deliberations': deliberations,
        'stats': stats,
        'recent_completed': recent_completed,
        'is_president': jury_member.is_president
    }
    
    return render(request, 'jury/dashboard.html', context)

@login_required
def jury_deliberations_list(request):
    """Liste des délibérations pour les membres du jury"""
    # Vérifier si l'utilisateur est un membre du jury
    try:
        jury_member = request.user.jurymember
    except JuryMember.DoesNotExist:
        messages.error(request, "Accès non autorisé. Vous n'êtes pas un membre du jury.")
        return redirect('belletin:dashboard')
    
    # Obtenir les promotions auxquelles le membre du jury appartient
    promotions = jury_member.promotions.all()
    
    # Initialiser le formulaire de filtre
    filter_form = DeliberationFilterForm(request.GET or None)
    
    # Base query - montrer toutes les délibérations liées aux promotions du jury
    # sans filtrer par statut initialement
    deliberations = Deliberation.objects.filter(
        promotion__in=promotions
    )
    
    # Appliquer les filtres si le formulaire est valide
    if filter_form.is_valid():
        data = filter_form.cleaned_data
        
        if data.get('faculty'):
            deliberations = deliberations.filter(
                promotion__department__faculty=data['faculty']
            )
        
        if data.get('department'):
            deliberations = deliberations.filter(
                promotion__department=data['department']
            )
        
        if data.get('promotion_level'):
            deliberations = deliberations.filter(
                promotion__level=data['promotion_level']
            )
        
        if data.get('semester'):
            deliberations = deliberations.filter(
                semester=data['semester']
            )
        
        if data.get('status'):
            deliberations = deliberations.filter(
                status=data['status']
            )
    
    # Ajouter des annotations pour les statistiques
    deliberations = deliberations.annotate(
        total_students=Count('studentdeliberation', distinct=True),
        validated_students=Count(
            'studentdeliberation',
            filter=Q(studentdeliberation__validated=True),
            distinct=True
        )
    ).order_by('-date_scheduled')  # Ordre chronologique inversé pour voir les récentes d'abord
    
    context = {
        'jury_member': jury_member,
        'deliberations': deliberations,
        'filter_form': filter_form,
        'is_president': jury_member.is_president
    }
    
    return render(request, 'jury/deliberations_list.html', context)

@login_required
def jury_create_deliberation(request):
    """Créer une nouvelle délibération"""
    # Vérifier si l'utilisateur est un président de jury
    try:
        jury_member = request.user.jurymember
        if not jury_member.is_president:
            messages.error(request, "Seuls les présidents de jury peuvent créer des délibérations.")
            return redirect('belletin:jury_deliberations_list')
    except JuryMember.DoesNotExist:
        messages.error(request, "Accès non autorisé. Vous n'êtes pas un membre du jury.")
        return redirect('belletin:dashboard')
    
    # Obtenir les promotions auxquelles le membre du jury appartient
    promotions = jury_member.promotions.all()
    
    if request.method == 'POST':
        form = DeliberationCreateForm(request.POST)
        
        # Limiter les choix de promotion aux promotions du jury
        form.fields['promotion'].queryset = promotions
        
        if form.is_valid():
            deliberation = form.save()
            
            # Ajouter ce membre du jury comme membre de la délibération
            DeliberationMember.objects.create(
                deliberation=deliberation,
                jury_member=jury_member,
                is_present=True
            )
            
            # Créer automatiquement les StudentDeliberation pour tous les étudiants de la promotion
            students = Student.objects.filter(promotion=deliberation.promotion)
            
            for student in students:
                # Calculer la moyenne et les crédits obtenus
                ues = UE.objects.filter(
                    promotion=deliberation.promotion,
                    semester=deliberation.semester
                )
                
                student_grades = Grade.objects.filter(
                    student=student,
                    ue__in=ues
                )
                
                # Calculer la moyenne
                total_points = 0
                total_credits = 0
                credits_obtained = 0
                
                for grade in student_grades:
                    if grade.cc is not None and grade.mc is not None:
                        ue_average = (grade.cc + grade.mc) / 2
                        total_points += ue_average * grade.ue.credits
                        total_credits += grade.ue.credits
                        
                        # Un étudiant obtient les crédits si sa moyenne est >= 10
                        if ue_average >= 10:
                            credits_obtained += grade.ue.credits
                
                average = total_points / total_credits if total_credits > 0 else 0
                
                # Déterminer la décision automatique selon les nouvelles règles
                # Pour passer en classe supérieure: au moins 45 crédits sur 60
                minimum_credits_for_promotion = 45
                
                if credits_obtained >= minimum_credits_for_promotion:
                    # L'étudiant a assez de crédits pour passer
                    if credits_obtained == total_credits:
                        # Tous les crédits obtenus (60/60)
                        auto_decision = 'ADMITTED'
                    else:
                        # Admis mais doit racheter les cours non validés
                        auto_decision = 'ADMITTED'
                elif average >= 8:
                    auto_decision = 'REMEDIAL'
                else:
                    auto_decision = 'FAILED'
                
                # Créer l'objet StudentDeliberation
                StudentDeliberation.objects.create(
                    deliberation=deliberation,
                    student=student,
                    average=average,
                    credits_obtained=credits_obtained,
                    auto_decision=auto_decision
                )
            
            messages.success(request, f"Délibération créée avec succès pour {deliberation.promotion} - S{deliberation.semester}.")
            return redirect('belletin:jury_deliberation_detail', deliberation_token=deliberation.token)
    else:
        form = DeliberationCreateForm()
        form.fields['promotion'].queryset = promotions
    
    context = {
        'form': form,
        'jury_member': jury_member
    }
    
    return render(request, 'jury/create_deliberation.html', context)

@login_required
def jury_deliberation_detail(request, deliberation_token):
    """Afficher les détails d'une délibération"""
    # Vérifier si l'utilisateur est un membre du jury
    try:
        jury_member = request.user.jurymember
    except JuryMember.DoesNotExist:
        messages.error(request, "Accès non autorisé. Vous n'êtes pas un membre du jury.")
        return redirect('belletin:dashboard')
    
    # Récupérer la délibération
    try:
        from .utils import resolve_deliberation_token
        deliberation = resolve_deliberation_token(deliberation_token)
    except Deliberation.DoesNotExist:
        messages.error(request, "Délibération introuvable.")
        return redirect('belletin:jury_deliberations_list')
    except Exception as e:
        messages.error(request, f"Erreur lors de l'accès à la délibération: {str(e)}")
        return redirect('belletin:jury_deliberations_list')
    
    # Vérifier que le membre du jury est associé à la promotion de la délibération
    if deliberation.promotion not in jury_member.promotions.all():
        messages.error(request, "Vous n'êtes pas autorisé à accéder à cette délibération.")
        return redirect('belletin:jury_deliberations_list')
    
    # Marquer le membre du jury comme présent (seulement si la délibération n'est pas encore complétée)
    if deliberation.status != 'COMPLETED':
        DeliberationMember.objects.get_or_create(
            deliberation=deliberation,
            jury_member=jury_member,
            defaults={'is_present': True}
        )
    
        # Si la délibération est en attente, la passer à "en cours" (seulement si pas encore complétée)
        if deliberation.status == 'PENDING':
            deliberation.status = 'IN_PROGRESS'
            deliberation.save()
    
    # Récupérer les décisions pour les étudiants
    student_deliberations = StudentDeliberation.objects.filter(
        deliberation=deliberation
    ).select_related('student', 'student__user', 'student__promotion')
    
    # Calculer les statistiques
    stats = {
        'total': student_deliberations.count(),
        'validated': student_deliberations.filter(validated=True).count(),
        'admitted': student_deliberations.filter(
            final_decision='ADMITTED'
        ).count(),
        'remedial': student_deliberations.filter(
            final_decision='REMEDIAL'
        ).count(),
        'failed': student_deliberations.filter(
            final_decision='FAILED'
        ).count(),
    }
    
    # Ajouter les pourcentages
    if stats['total'] > 0:
        stats['validated_percent'] = (stats['validated'] / stats['total']) * 100
        
        # Pour les décisions finales, calculer sur celles qui ont été validées
        if stats['validated'] > 0:
            stats['admitted_percent'] = (stats['admitted'] / stats['validated']) * 100
            stats['remedial_percent'] = (stats['remedial'] / stats['validated']) * 100
            stats['failed_percent'] = (stats['failed'] / stats['validated']) * 100
    
    # Déterminer si toutes les délibérations sont validées (pour activer le bouton de finalisation)
    can_complete = stats['validated'] == stats['total']
    
    # Obtenir les autres membres du jury présents
    jury_members = DeliberationMember.objects.filter(
        deliberation=deliberation,
        is_present=True
    ).select_related('jury_member', 'jury_member__user')
    
    context = {
        'deliberation': deliberation,
        'student_deliberations': student_deliberations,
        'stats': stats,
        'total_students': stats['total'],
        'validated_count': stats['validated'],
        'admitted_count': stats['admitted'],
        'remedial_count': stats['remedial'],
        'failed_count': stats['failed'],
        'admitted_percent': stats.get('admitted_percent', 0),
        'remedial_percent': stats.get('remedial_percent', 0),
        'failed_percent': stats.get('failed_percent', 0),
        'jury_members': jury_members,
        'jury_member': jury_member,
        'is_president': jury_member.is_president,
        'can_complete': can_complete
    }
    
    return render(request, 'jury/deliberation_detail.html', context)

@login_required
def jury_student_detail(request, deliberation_token, student_id):
    """Afficher les détails d'un étudiant dans une délibération"""
    # Vérifier si l'utilisateur est un membre du jury
    try:
        jury_member = request.user.jurymember
    except JuryMember.DoesNotExist:
        messages.error(request, "Accès non autorisé. Vous n'êtes pas un membre du jury.")
        return redirect('belletin:dashboard')
    
    # Récupérer la délibération
    try:
        from .utils import resolve_deliberation_token
        deliberation = resolve_deliberation_token(deliberation_token)
    except Deliberation.DoesNotExist:
        messages.error(request, "Délibération introuvable.")
        return redirect('belletin:jury_deliberations_list')
    except Exception as e:
        messages.error(request, f"Erreur lors de l'accès à la délibération: {str(e)}")
        return redirect('belletin:jury_deliberations_list')
    
    student = get_object_or_404(Student, id=student_id)
    
    # Vérifier que le membre du jury est associé à la promotion de la délibération
    if deliberation.promotion not in jury_member.promotions.all():
        messages.error(request, "Vous n'êtes pas autorisé à accéder à cette délibération.")
        return redirect('belletin:jury_deliberations_list')
    
    # Obtenir la décision pour cet étudiant
    student_deliberation = get_object_or_404(
        StudentDeliberation, 
        deliberation=deliberation,
        student=student
    )
    
    # Obtenir les notes de l'étudiant pour ce semestre
    ues = UE.objects.filter(
        promotion=deliberation.promotion,
        semester=deliberation.semester
    )
    
    grades = Grade.objects.filter(
        student=student,
        ue__in=ues
    ).select_related('ue')
    
    # Obtenir les composantes de notes détaillées
    courses = Course.objects.filter(
        ue__in=ues,
        academic_year=deliberation.academic_year
    )
    
    components = GradeComponent.objects.filter(
        student=student,
        course__in=courses
    ).select_related('course', 'course__ue', 'course__professor')
    
    # Formulaire de décision
    if request.method == 'POST':
        form = StudentDeliberationDecisionForm(request.POST, instance=student_deliberation)
        
        if form.is_valid():
            # Sauvegarder le formulaire sans commit pour ajouter des champs
            decision = form.save(commit=False)
            
            # Si la décision a changé, enregistrer dans le log
            if 'final_decision' in form.changed_data and student_deliberation.final_decision:
                DeliberationChangeLog.objects.create(
                    student_deliberation=student_deliberation,
                    previous_decision=student_deliberation.final_decision,
                    new_decision=decision.final_decision,
                    changed_by=request.user,
                    reason=decision.comments
                )
            
            # Marquer comme validé si non validé précédemment
            if not student_deliberation.validated:
                decision.validated = True
                decision.validated_by = request.user
                decision.validated_at = timezone.now()
            
            decision.save()
            
            messages.success(request, f"Décision enregistrée pour {student.user.get_full_name()}.")
            return redirect('belletin:jury_deliberation_detail', deliberation_token=deliberation.token)
    else:
        form = StudentDeliberationDecisionForm(instance=student_deliberation)
    
    # Obtenir l'historique des modifications
    change_logs = DeliberationChangeLog.objects.filter(
        student_deliberation=student_deliberation
    ).order_by('-changed_at')
    
    context = {
        'deliberation': deliberation,
        'student': student,
        'student_deliberation': student_deliberation,
        'grades': grades,
        'components': components,
        'form': form,
        'change_logs': change_logs,
        'jury_member': jury_member,
        'is_president': jury_member.is_president
    }
    
    return render(request, 'jury/student_detail.html', context)

@login_required
def jury_bulk_decision(request, deliberation_token):
    """Appliquer une décision à plusieurs étudiants"""
    # Vérifier si l'utilisateur est un président de jury
    try:
        jury_member = request.user.jurymember
        if not jury_member.is_president:
            messages.error(request, "Seuls les présidents de jury peuvent prendre des décisions en masse.")
            return redirect('belletin:jury_deliberation_detail', deliberation_token=deliberation_token)
    except JuryMember.DoesNotExist:
        messages.error(request, "Accès non autorisé. Vous n'êtes pas un membre du jury.")
        return redirect('belletin:dashboard')
    
    # Récupérer la délibération
    try:
        from .utils import resolve_deliberation_token
        deliberation = resolve_deliberation_token(deliberation_token)
    except Deliberation.DoesNotExist:
        messages.error(request, "Délibération introuvable.")
        return redirect('belletin:jury_deliberations_list')
    except Exception as e:
        messages.error(request, f"Erreur lors de l'accès à la délibération: {str(e)}")
        return redirect('belletin:jury_deliberations_list')
    
    # Vérifier que le membre du jury est associé à la promotion de la délibération
    if deliberation.promotion not in jury_member.promotions.all():
        messages.error(request, "Vous n'êtes pas autorisé à accéder à cette délibération.")
        return redirect('belletin:jury_deliberations_list')
    
    if request.method == 'POST':
        form = StudentDeliberationBulkForm(request.POST, deliberation_token=deliberation_token)
        
        if form.is_valid():
            students = form.cleaned_data['students']
            decision = form.cleaned_data['decision']
            reason = form.cleaned_data['reason']
            
            # Mise à jour en masse
            with transaction.atomic():
                for student in students:
                    student_deliberation = StudentDeliberation.objects.get(
                        deliberation=deliberation,
                        student=student
                    )
                    
                    # Si la décision a changé, enregistrer dans le log
                    if student_deliberation.final_decision != decision:
                        DeliberationChangeLog.objects.create(
                            student_deliberation=student_deliberation,
                            previous_decision=student_deliberation.final_decision or student_deliberation.auto_decision,
                            new_decision=decision,
                            changed_by=request.user,
                            reason=reason
                        )
                    
                    # Mettre à jour la décision
                    student_deliberation.final_decision = decision
                    student_deliberation.comments = reason
                    student_deliberation.validated = True
                    student_deliberation.validated_by = request.user
                    student_deliberation.validated_at = timezone.now()
                    student_deliberation.save()
            
            messages.success(request, f"Décision appliquée à {len(students)} étudiants.")
            return redirect('belletin:jury_deliberation_detail', deliberation_token=deliberation.token)
    else:
        form = StudentDeliberationBulkForm(deliberation_token=deliberation_token)
    
    context = {
        'deliberation': deliberation,
        'form': form,
        'jury_member': jury_member
    }
    
    return render(request, 'jury/bulk_decision.html', context)

@login_required
def jury_complete_deliberation(request, deliberation_token):
    """Finaliser une délibération"""
    # Vérifier si l'utilisateur est un président de jury
    try:
        jury_member = request.user.jurymember
        if not jury_member.is_president:
            messages.error(request, "Seuls les présidents de jury peuvent finaliser une délibération.")
            return redirect('belletin:jury_deliberation_detail', deliberation_token=deliberation_token)
    except JuryMember.DoesNotExist:
        messages.error(request, "Accès non autorisé. Vous n'êtes pas un membre du jury.")
        return redirect('belletin:dashboard')
    
    # Récupérer la délibération
    try:
        from .utils import resolve_deliberation_token
        deliberation = resolve_deliberation_token(deliberation_token)
    except Deliberation.DoesNotExist:
        messages.error(request, "Délibération introuvable.")
        return redirect('belletin:jury_deliberations_list')
    except Exception as e:
        messages.error(request, f"Erreur lors de l'accès à la délibération: {str(e)}")
        return redirect('belletin:jury_deliberations_list')
    
    # Vérifier que le membre du jury est associé à la promotion de la délibération
    if deliberation.promotion not in jury_member.promotions.all():
        messages.error(request, "Vous n'êtes pas autorisé à accéder à cette délibération.")
        return redirect('belletin:jury_deliberations_list')
    
    # Vérifier que toutes les décisions ont été validées
    student_count = StudentDeliberation.objects.filter(deliberation=deliberation).count()
    validated_count = StudentDeliberation.objects.filter(
        deliberation=deliberation, 
        validated=True
    ).count()
    
    if validated_count < student_count:
        messages.error(
            request, 
            f"Impossible de finaliser la délibération. {student_count - validated_count} étudiants n'ont pas de décision validée."
        )
        return redirect('belletin:jury_deliberation_detail', deliberation_token=deliberation.token)
    
    # Si c'est une requête POST et toutes les conditions sont remplies, finaliser la délibération
    if request.method == 'POST':
        # Mettre à jour le statut et la date de fin
        deliberation.status = 'COMPLETED'
        deliberation.date_completed = timezone.now()
        deliberation.save()
        
        messages.success(request, "Délibération finalisée avec succès.")
    
    return redirect('belletin:jury_deliberation_detail', deliberation_token=deliberation.token)

@login_required
def jury_export_pv(request, deliberation_token):
    """Exporter le procès-verbal en PDF"""
    # Vérifier si l'utilisateur est un membre du jury
    try:
        jury_member = request.user.jurymember
    except JuryMember.DoesNotExist:
        messages.error(request, "Accès non autorisé. Vous n'êtes pas un membre du jury.")
        return redirect('belletin:dashboard')
    
    # Récupérer la délibération
    try:
        from .utils import resolve_deliberation_token
        deliberation = resolve_deliberation_token(deliberation_token)
    except Deliberation.DoesNotExist:
        messages.error(request, "Délibération introuvable.")
        return redirect('belletin:jury_deliberations_list')
    except Exception as e:
        messages.error(request, f"Erreur lors de l'accès à la délibération: {str(e)}")
        return redirect('belletin:jury_deliberations_list')
    
    # Vérifier que le membre du jury est associé à la promotion de la délibération
    if deliberation.promotion not in jury_member.promotions.all():
        messages.error(request, "Vous n'êtes pas autorisé à accéder à cette délibération.")
        return redirect('belletin:jury_deliberations_list')
    
    # Vérifier que la délibération est complétée
    if deliberation.status != 'COMPLETED':
        messages.error(request, "Le procès-verbal ne peut être généré que pour une délibération finalisée.")
        return redirect('belletin:jury_deliberation_detail', deliberation_token=deliberation.token)
    
    # Récupérer les données nécessaires
    student_deliberations = StudentDeliberation.objects.filter(
        deliberation=deliberation
    ).select_related(
        'student', 'student__user', 'student__promotion',
        'validated_by'
    ).order_by('student__matricule')
    
    jury_members = DeliberationMember.objects.filter(
        deliberation=deliberation,
        is_present=True
    ).select_related('jury_member', 'jury_member__user')
    
    # Calculer les statistiques
    stats = {
        'total': student_deliberations.count(),
        'admitted': student_deliberations.filter(final_decision='ADMITTED').count(),
        'remedial': student_deliberations.filter(final_decision='REMEDIAL').count(),
        'failed': student_deliberations.filter(final_decision='FAILED').count()
    }
    
    # Calcul des pourcentages
    if stats['total'] > 0:
        stats['admitted_percent'] = (stats['admitted'] / stats['total']) * 100
        stats['remedial_percent'] = (stats['remedial'] / stats['total']) * 100
        stats['failed_percent'] = (stats['failed'] / stats['total']) * 100
    
    # Préparer le contexte pour le template
    context = {
        'deliberation': deliberation,
        'student_deliberations': student_deliberations,
        'jury_members': jury_members,
        'stats': stats,
        'date': timezone.now()
    }
    
    # Générer le HTML
    html_string = render_to_string('jury/pv_template.html', context)
    
    # Generate HTML response first - this will be our fallback
    response = HttpResponse(html_string, content_type='text/html')
    
    # Try to convert to PDF if possible
    pdf_available = False
    try:
        # Import WeasyPrint directly here to ensure it's in scope
        from weasyprint import HTML as WeasyHTML
        pdf = WeasyHTML(string=html_string).write_pdf()
        pdf_available = True
    except Exception as e:
        # If anything goes wrong with PDF generation, we'll use HTML
        messages.warning(
            request, 
            f"Impossible de générer un PDF, affichage HTML: {str(e)}"
        )
    
    # Return PDF if available, otherwise return the HTML response
    if pdf_available:
        pdf_response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"PV_Deliberation_{deliberation.promotion}_{deliberation.academic_year}.pdf"
        pdf_response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return pdf_response
    
    return response

@login_required
def jury_export_data(request, deliberation_token):
    """Exporter les données de délibération en CSV"""
    # Vérifier si l'utilisateur est un membre du jury
    try:
        jury_member = request.user.jurymember
    except JuryMember.DoesNotExist:
        messages.error(request, "Accès non autorisé. Vous n'êtes pas un membre du jury.")
        return redirect('belletin:dashboard')
    
    # Récupérer la délibération
    try:
        from .utils import resolve_deliberation_token
        deliberation = resolve_deliberation_token(deliberation_token)
    except Deliberation.DoesNotExist:
        messages.error(request, "Délibération introuvable.")
        return redirect('belletin:jury_deliberations_list')
    except Exception as e:
        messages.error(request, f"Erreur lors de l'accès à la délibération: {str(e)}")
        return redirect('belletin:jury_deliberations_list')
    
    # Vérifier que le membre du jury est associé à la promotion de la délibération
    if deliberation.promotion not in jury_member.promotions.all():
        messages.error(request, "Vous n'êtes pas autorisé à accéder à cette délibération.")
        return redirect('belletin:jury_deliberations_list')
    
    # Récupérer les données nécessaires
    student_deliberations = StudentDeliberation.objects.filter(
        deliberation=deliberation
    ).select_related(
        'student', 'student__user', 'student__promotion',
        'validated_by'
    ).order_by('student__matricule')
    
    # Préparer la réponse CSV
    response = HttpResponse(content_type='text/csv')
    filename = f"Deliberation_{deliberation.promotion}_{deliberation.academic_year}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Créer le writer CSV
    writer = csv.writer(response)
    
    # Écrire l'en-tête
    writer.writerow([
        'Matricule', 'Nom', 'Prénom', 'Promotion', 'Département',
        'Moyenne', 'Crédits Obtenus', 'Décision Automatique', 
        'Décision Finale', 'Validé Par', 'Date de Validation', 'Commentaires'
    ])
    
    # Écrire les données
    for delib in student_deliberations:
        writer.writerow([
            delib.student.matricule,
            delib.student.user.last_name,
            delib.student.user.first_name,
            delib.student.promotion.get_level_display(),
            delib.student.promotion.department.name,
            f"{delib.average:.2f}",
            delib.credits_obtained,
            delib.get_auto_decision_display(),
            delib.get_final_decision_display() if delib.final_decision else '',
            delib.validated_by.get_full_name() if delib.validated_by else '',
            delib.validated_at.strftime('%d/%m/%Y %H:%M') if delib.validated_at else '',
            delib.comments
        ])
    
    return response

# Vues pour les étudiants (bulletins)

def determine_auto_decision(total_credits_obtained, annual_average):
    """
    Détermine la décision automatique de promotion selon les critères:
    - 45+ crédits = Admis
    - Entre 40-44 crédits avec moyenne > 8 = Rattrapage
    - Moins de 40 crédits ou moyenne < 8 = Redoublement
    
    Returns:
        tuple: (auto_decision code, decision explanation)
    """
    minimum_credits_for_promotion = 45
    
    if total_credits_obtained >= minimum_credits_for_promotion:
        return ('ADMITTED', f"Admis(e) en classe supérieure avec {total_credits_obtained} crédits (minimum requis: 45)")
    elif total_credits_obtained >= 40 and annual_average >= 8:
        return ('REMEDIAL', f"Rattrapage possible avec {total_credits_obtained} crédits et moyenne de {annual_average:.2f}/20")
    else:
        if annual_average < 8:
            return ('FAILED', f"Redoublement - Moyenne insuffisante ({annual_average:.2f}/20 < 8/20)")
        else:
            return ('FAILED', f"Redoublement - Crédits insuffisants ({total_credits_obtained} < 40)")

@login_required
def student_bulletin(request):
    """Afficher le bulletin de l'étudiant connecté"""
    # Vérifier si l'utilisateur est un étudiant
    try:
        student = request.user.student
    except Student.DoesNotExist:
        messages.error(request, "Accès non autorisé. Vous n'êtes pas un étudiant.")
        return redirect('belletin:dashboard')
    
    # Obtenir l'année académique actuelle
    current_year = AcademicYear.objects.last()
    
    # Obtenir toutes les délibérations pour l'étudiant (même celles en attente)
    deliberations = StudentDeliberation.objects.filter(
        student=student
    ).select_related('deliberation')
    
    # Variable pour suivre si des délibérations existent
    has_any_deliberation = False
    
    # Si aucune délibération n'existe pour l'étudiant, vérifier s'il existe des délibérations pour sa promotion
    if not deliberations.exists():
        # Vérifier s'il existe des délibérations pour la promotion de l'étudiant
        promotion_deliberations = Deliberation.objects.filter(
            promotion=student.promotion
        ).exists()
        
        if not promotion_deliberations:
            # Aucune délibération n'existe pour cette promotion
            messages.info(request, "Aucune délibération n'a encore été créée pour votre promotion. Veuillez patienter jusqu'à ce que le jury planifie une délibération.")
        else:
            # Des délibérations existent pour la promotion mais l'étudiant n'y est pas associé
            messages.info(request, "Des délibérations existent pour votre promotion mais aucune n'est encore disponible pour vous. Veuillez contacter votre responsable académique si vous pensez qu'il s'agit d'une erreur.")
        
        # On ne tente plus de créer automatiquement des délibérations comme auparavant
        has_any_deliberation = False
    else:
        has_any_deliberation = True
    
    # Obtenir les notes de l'étudiant
    grades = Grade.objects.filter(
        student=student
    ).select_related('ue')
    
    # Composantes détaillées des notes
    components = GradeComponent.objects.filter(
        student=student
    ).select_related('course', 'course__ue', 'course__professor')
    
    context = {
        'student': student,
        'deliberations': deliberations,
        'grades': grades,
        'components': components,
        'current_year': current_year,
        'has_any_deliberation': has_any_deliberation
    }
    
    return render(request, 'student/bulletin.html', context)

@login_required
def student_download_bulletin(request, deliberation_id):
    """Télécharger le bulletin d'un semestre au format PDF"""
    # Vérifier si l'utilisateur est un étudiant
    try:
        student = request.user.student
    except Student.DoesNotExist:
        messages.error(request, "Accès non autorisé. Vous n'êtes pas un étudiant.")
        return redirect('belletin:dashboard')
    
    # Obtenir la délibération - deux méthodes possibles
    try:
        # Essai 1: Par ID numérique
        try:
            deliberation = Deliberation.objects.get(id=deliberation_id)
        except (ValueError, Deliberation.DoesNotExist):
            # Essai 2: Par token
            try:
                deliberation = Deliberation.objects.get(token=deliberation_id)
            except Deliberation.DoesNotExist:
                # Essai 3: Par décodage du token
                try:
                    from .utils import decode_id
                    delib_id = decode_id(deliberation_id, expected_model='Deliberation')
                    deliberation = Deliberation.objects.get(id=delib_id)
                except Exception:
                    # Si tous les essais échouent, essayer de trouver une délibération par promotion
                    deliberation = Deliberation.objects.filter(
                        promotion=student.promotion, 
                        status='COMPLETED'
                    ).order_by('-date_scheduled').first()
                    
                    if not deliberation:
                        # Vraiment aucune délibération trouvée
                        messages.error(request, "Délibération introuvable. Veuillez contacter l'administration.")
                        return redirect('belletin:student_bulletin')
        
        # Une fois que nous avons la délibération, vérifier si l'étudiant y est associé
        student_deliberation = StudentDeliberation.objects.filter(
            deliberation=deliberation,
            student=student
        ).first()
        
        # Si l'étudiant n'est pas associé à cette délibération, créer l'association
        if not student_deliberation:
            student_deliberation = StudentDeliberation(
                deliberation=deliberation,
                student=student,
                average=0,
                credits_obtained=0,
                auto_decision='ADMITTED',
                validated=True,
                validated_at=timezone.now()
            )
            student_deliberation.save()
        
        # Obtenir les notes de l'étudiant pour ce semestre
        ues = UE.objects.filter(
            promotion=deliberation.promotion,
            semester=deliberation.semester
        )
        
        grades = Grade.objects.filter(
            student=student,
            ue__in=ues
        ).select_related('ue')
        
        # Obtenir les composantes de notes détaillées
        courses = Course.objects.filter(
            ue__in=ues,
            academic_year=deliberation.academic_year
        )
        
        components = GradeComponent.objects.filter(
            student=student,
            course__in=courses
        ).select_related('course', 'course__ue', 'course__professor')
        
        # Préparer le contexte pour le template
        context = {
            'student': student,
            'deliberation': deliberation,
            'student_deliberation': student_deliberation,
            'grades': grades,
            'components': components,
            'date': timezone.now()
        }
        
        # Générer le HTML
        try:
            html_string = render_to_string('student/bulletin_template.html', context)
            print(f"HTML généré avec succès pour le bulletin de {student.matricule}")
        except Exception as template_error:
            print(f"Erreur lors du rendu du template bulletin_template.html: {str(template_error)}")
            raise template_error
        
        # Generate HTML response first - this will be our fallback
        response = HttpResponse(html_string, content_type='text/html')
        
        # Try to convert to PDF if possible
        try:
            # Vérifier d'abord si les bibliothèques requises sont disponibles
            try:
                import gi
                gi.require_version('Gtk', '3.0')
                import cairo
            except (ImportError, ValueError):
                # Bibliothèques GTK non disponibles, on sert silencieusement le HTML
                return response
            
            # Import WeasyPrint directly here to ensure it's in scope
            from weasyprint import HTML as WeasyHTML
            print("Tentative de génération du PDF...")
            pdf = WeasyHTML(string=html_string).write_pdf()
            print("PDF généré avec succès")
            
            pdf_available = True
            pdf_response = HttpResponse(pdf, content_type='application/pdf')
            filename = f"Bulletin_{student.matricule}_{deliberation.promotion}_{deliberation.semester}.pdf"
            pdf_response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return pdf_response
        except Exception as pdf_error:
            # Vérifier si c'est une erreur connue liée aux bibliothèques GTK/GObject
            error_msg = str(pdf_error)
            if "gobject" in error_msg.lower() or "gtk" in error_msg.lower() or "ctypes.util.find_library()" in error_msg:
                # Erreur liée aux dépendances de WeasyPrint sur Windows
                # Servir silencieusement la version HTML sans afficher d'erreur
                print(f"Erreur connue de WeasyPrint (dépendances GTK): {error_msg}")
                return response
            
            # Pour les autres erreurs, afficher un message plus générique
            print(f"Erreur lors de la génération du PDF: {error_msg}")
            # Ne pas afficher de message d'erreur à l'utilisateur
            return response
        
    except Exception as e:
        # Journaliser l'erreur
        print(f"Erreur lors de la génération du bulletin: {str(e)}")
        messages.error(request, "Une erreur est survenue lors de la génération du bulletin. Veuillez réessayer plus tard.")
        return redirect('belletin:student_bulletin')

@login_required
def student_download_bulletin_coupon(request, deliberation_id):
    """Télécharger le relevé de notes avec bulletin"""
    # Vérifier si l'utilisateur est un étudiant
    try:
        student = request.user.student
    except Student.DoesNotExist:
        messages.error(request, "Accès non autorisé. Vous n'êtes pas un étudiant.")
        return redirect('belletin:dashboard')
    
    # Obtenir la délibération - deux méthodes possibles
    try:
        # Essai 1: Par ID numérique
        try:
            deliberation = Deliberation.objects.get(id=deliberation_id)
        except (ValueError, Deliberation.DoesNotExist):
            # Essai 2: Par token
            try:
                deliberation = Deliberation.objects.get(token=deliberation_id)
            except Deliberation.DoesNotExist:
                # Essai 3: Par décodage du token
                try:
                    from .utils import decode_id
                    delib_id = decode_id(deliberation_id, expected_model='Deliberation')
                    deliberation = Deliberation.objects.get(id=delib_id)
                except Exception:
                    # Si tous les essais échouent, essayer de trouver une délibération par promotion
                    deliberation = Deliberation.objects.filter(
                        promotion=student.promotion, 
                        status='COMPLETED'
                    ).order_by('-date_scheduled').first()
                    
                    if not deliberation:
                        # Vraiment aucune délibération trouvée
                        messages.error(request, "Délibération introuvable. Veuillez contacter l'administration.")
                        return redirect('belletin:student_bulletin')
        
        # Une fois que nous avons la délibération, vérifier si l'étudiant y est associé
        student_deliberation = StudentDeliberation.objects.filter(
            deliberation=deliberation,
            student=student
        ).first()
        
        # Si l'étudiant n'est pas associé à cette délibération, créer l'association
        if not student_deliberation:
            student_deliberation = StudentDeliberation(
                deliberation=deliberation,
                student=student,
                average=0,
                credits_obtained=0,
                auto_decision='ADMITTED',
                validated=True,
                validated_at=timezone.now()
            )
            student_deliberation.save()
        
        # Obtenir les notes de l'étudiant pour ce semestre et tous les semestres précédents
        promotion = deliberation.promotion
        all_ues = UE.objects.filter(promotion=promotion, semester__lte=deliberation.semester)
        
        grades = Grade.objects.filter(
            student=student,
            ue__in=all_ues
        ).select_related('ue')
        
        # Calcul des statistiques pour le semestre 1
        semester1_grades = grades.filter(ue__semester=1)
        semester1_points = 0
        semester1_credits_total = 0
        semester1_credits_obtained = 0
        
        for grade in semester1_grades:
            if grade.cc is not None and grade.mc is not None:
                ue_average = (grade.cc + grade.mc) / 2
                semester1_points += ue_average * grade.ue.credits
                semester1_credits_total += grade.ue.credits
                
                if ue_average >= 10:
                    semester1_credits_obtained += grade.ue.credits
        
        if semester1_credits_total > 0:
            semester1_average = semester1_points / semester1_credits_total
            semester1_max_points = semester1_credits_total * 20
            semester1_percentage = (semester1_points / semester1_max_points) * 100
        else:
            semester1_average = 0
            semester1_max_points = 0
            semester1_percentage = 0
        
        # Calcul des statistiques pour le semestre 2
        semester2_grades = grades.filter(ue__semester=2)
        semester2_points = 0
        semester2_credits_total = 0
        semester2_credits_obtained = 0
        
        for grade in semester2_grades:
            if grade.cc is not None and grade.mc is not None:
                ue_average = (grade.cc + grade.mc) / 2
                semester2_points += ue_average * grade.ue.credits
                semester2_credits_total += grade.ue.credits
                
                if ue_average >= 10:
                    semester2_credits_obtained += grade.ue.credits
        
        if semester2_credits_total > 0:
            semester2_average = semester2_points / semester2_credits_total
            semester2_max_points = semester2_credits_total * 20
            semester2_percentage = (semester2_points / semester2_max_points) * 100
        else:
            semester2_average = 0
            semester2_max_points = 0
            semester2_percentage = 0
        
        # Calcul des statistiques annuelles
        total_points = semester1_points + semester2_points
        total_credits_available = semester1_credits_total + semester2_credits_total
        total_credits_obtained = semester1_credits_obtained + semester2_credits_obtained
        credits_to_complete = total_credits_available - total_credits_obtained
        
        # Calcul de la moyenne annuelle selon le système LMD
        if total_credits_available > 0:
            annual_average = total_points / total_credits_available
        else:
            annual_average = 0
        
        # Points maximum possibles (20 points par crédit)
        max_points = total_credits_available * 20
        
        # Calcul du pourcentage de réussite selon le système LMD
        if max_points > 0:
            success_percentage = (total_points / max_points) * 100
        else:
            success_percentage = 0
        
        # Calcul du pourcentage de crédits obtenus
        if total_credits_available > 0:
            credit_percentage = (total_credits_obtained / total_credits_available) * 100
        else:
            credit_percentage = 0
        
        # Définir le minimum de crédits requis pour la promotion
        minimum_credits_for_promotion = 45
        
        # Déterminer la décision automatique selon les critères:
        # - 45+ crédits = Admis
        # - Entre 40-44 crédits avec moyenne > 8 = Rattrapage
        # - Moins de 40 crédits ou moyenne < 8 = Redoublement
        if total_credits_obtained >= minimum_credits_for_promotion:
            auto_decision = 'ADMITTED'
            decision_explanation = "Admis(e) en classe supérieure avec {} crédits sur {} (minimum requis: 45)".format(
                total_credits_obtained, total_credits_available
            )
        elif total_credits_obtained >= 40 and annual_average >= 8:
            auto_decision = 'REMEDIAL'
            decision_explanation = "Rattrapage possible avec {} crédits et moyenne de {:.2f}/20".format(
                total_credits_obtained, annual_average
            )
        else:
            auto_decision = 'FAILED'
            if annual_average < 8:
                decision_explanation = "Redoublement - Moyenne insuffisante ({:.2f}/20 < 8/20)".format(annual_average)
            else:
                decision_explanation = "Redoublement - Crédits insuffisants ({} < 40)".format(total_credits_obtained)
        
        # Mettre à jour la délibération de l'étudiant avec les nouvelles valeurs calculées
        if student_deliberation:
            student_deliberation.average = annual_average
            student_deliberation.credits_obtained = total_credits_obtained
            student_deliberation.auto_decision = auto_decision
            student_deliberation.save()
        
        # Identifier les cours à rattraper (moyenne < 10)
        courses_to_retake = []
        for grade in grades:
            if grade.cc is not None and grade.mc is not None:
                ue_average = (grade.cc + grade.mc) / 2
                if ue_average < 10:
                    courses_to_retake.append({
                        'ue': grade.ue,
                        'average': ue_average
                    })
        
        # Déterminer si l'étudiant est admis avec des cours à racheter
        has_courses_to_retake = (total_credits_obtained >= minimum_credits_for_promotion and 
                                total_credits_obtained < total_credits_available)
        
        # Préparer le contexte
        context = {
            'student': student,
            'deliberation': deliberation,
            'student_deliberation': student_deliberation,
            'grades': grades,
            'date': timezone.now(),
            'semester1_average': semester1_average,
            'semester1_credits': semester1_credits_obtained,
            'semester1_total_credits': semester1_credits_total,
            'semester1_percentage': semester1_percentage,
            'semester2_average': semester2_average,
            'semester2_credits': semester2_credits_obtained,
            'semester2_total_credits': semester2_credits_total,
            'semester2_percentage': semester2_percentage,
            'total_points': total_points,
            'max_points': max_points,
            'success_percentage': success_percentage,
            'credit_percentage': credit_percentage,
            'credits_to_complete': credits_to_complete,
            'total_credits_obtained': total_credits_obtained,
            'total_credits_available': total_credits_available,
            'courses_to_retake': courses_to_retake,
            'has_courses_to_retake': has_courses_to_retake,
            'minimum_credits_for_promotion': minimum_credits_for_promotion,
            'decision_explanation': decision_explanation
        }
        
        # Générer le HTML avec le template approprié
        try:
            html_string = render_to_string('student/bulletin_coupon.html', context)
            print(f"HTML généré avec succès pour le bulletin coupon de {student.matricule}")
        except Exception as template_error:
            print(f"Erreur lors du rendu du template bulletin_coupon.html: {str(template_error)}")
            raise template_error
        
        # Générer la réponse HTML d'abord (fallback)
        response = HttpResponse(html_string, content_type='text/html')
        
        # Essayer de convertir en PDF si possible
        try:
            # Vérifier d'abord si les bibliothèques requises sont disponibles
            try:
                import gi
                gi.require_version('Gtk', '3.0')
                import cairo
            except (ImportError, ValueError):
                # Bibliothèques GTK non disponibles, on sert silencieusement le HTML
                return response
                
            from weasyprint import HTML as WeasyHTML
            print("Tentative de génération du PDF...")
            pdf = WeasyHTML(string=html_string).write_pdf()
            print("PDF généré avec succès")
            
            pdf_response = HttpResponse(pdf, content_type='application/pdf')
            filename = f"Releve_Complet_{student.matricule}_{deliberation.promotion}.pdf"
            pdf_response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return pdf_response
        except Exception as pdf_error:
            # Vérifier si c'est une erreur connue liée aux bibliothèques GTK/GObject
            error_msg = str(pdf_error)
            if "gobject" in error_msg.lower() or "gtk" in error_msg.lower() or "ctypes.util.find_library()" in error_msg:
                # Erreur liée aux dépendances de WeasyPrint sur Windows
                # Servir silencieusement la version HTML sans afficher d'erreur
                print(f"Erreur connue de WeasyPrint (dépendances GTK): {error_msg}")
                return response
            
            # Pour les autres erreurs, afficher un message plus générique
            print(f"Erreur lors de la génération du PDF: {error_msg}")
            # Ne pas afficher de message d'erreur à l'utilisateur
            return response
    
    except Exception as e:
        # Journaliser l'erreur
        print(f"Erreur lors de la génération du relevé de notes: {str(e)}")
        messages.error(request, "Une erreur est survenue lors de la génération du relevé de notes. Veuillez réessayer plus tard.")
        return redirect('belletin:student_bulletin')

@login_required
def admin_new_academic_year(request):
    """Vue pour créer une nouvelle année académique et gérer la promotion des étudiants"""
    # Vérifier que l'utilisateur est administrateur
    if not request.user.is_staff:
        messages.error(request, "Accès non autorisé. Vous n'êtes pas administrateur.")
        return redirect('belletin:dashboard')
    
    # Obtenir l'année académique actuelle
    current_year = AcademicYear.objects.filter(is_current=True).first()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create_year':
            # Créer une nouvelle année académique
            year_name = request.POST.get('year_name')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            
            if year_name and start_date and end_date:
                new_year = AcademicYear.objects.create(
                    name=year_name,
                    start_date=start_date,
                    end_date=end_date,
                    is_current=True  # Marquer comme année courante
                )
                
                messages.success(request, f"Nouvelle année académique créée: {new_year.name}")
                return redirect('belletin:admin_promote_students', year_id=new_year.id)
            else:
                messages.error(request, "Veuillez remplir tous les champs.")
        
        elif action == 'promote_students' and current_year:
            # Rediriger vers la vue de promotion des étudiants
            return redirect('belletin:admin_promote_students', year_id=current_year.id)
    
    context = {
        'current_year': current_year,
        'previous_years': AcademicYear.objects.filter(is_current=False).order_by('-end_date')[:5]
    }
    
    return render(request, 'belletin/admin/new_academic_year.html', context)

@login_required
def admin_promote_students(request, year_id):
    """Vue pour promouvoir les étudiants qui remplissent les conditions LMD"""
    # Vérifier que l'utilisateur est administrateur
    if not request.user.is_staff:
        messages.error(request, "Accès non autorisé. Vous n'êtes pas administrateur.")
        return redirect('belletin:dashboard')
    
    # Obtenir l'année académique
    academic_year = get_object_or_404(AcademicYear, id=year_id)
    
    # Obtenir l'année académique précédente
    previous_year = AcademicYear.objects.filter(
        end_date__lt=academic_year.start_date
    ).order_by('-end_date').first()
    
    if not previous_year:
        messages.warning(request, "Aucune année académique précédente trouvée.")
    
    # Statistiques pour le résumé
    stats = {
        'total_students': 0,
        'promoted': 0,
        'remedial': 0,
        'failed': 0,
        'processed': 0
    }
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'process_promotions':
            # Traiter toutes les promotions en une seule opération
            with transaction.atomic():
                # Pour chaque niveau, récupérer les étudiants
                for level in ['L1', 'L2', 'L3', 'M1', 'M2']:
                    # Ignorer M2 car c'est déjà le niveau le plus élevé
                    if level == 'M2':
                        continue
                    
                    process_student_promotions(level, previous_year, academic_year, stats)
            
            messages.success(request, 
                             f"Promotion terminée: {stats['promoted']} admis, {stats['remedial']} en rattrapage, "
                             f"{stats['failed']} ajournés sur {stats['total_students']} étudiants.")
            return redirect('belletin:admin_new_academic_year')
    
    # Obtenir tous les niveaux avec leur nombre d'étudiants
    promotions = Promotion.objects.all()
    levels_stats = {}
    
    for promotion in promotions:
        level = promotion.get_level_display()
        if level not in levels_stats:
            levels_stats[level] = {
                'total': 0,
                'department': promotion.department.name,
                'next_level': get_next_level(promotion.level)
            }
        
        # Compter les étudiants par niveau
        student_count = Student.objects.filter(
            promotion=promotion,
            current_academic_year=previous_year
        ).count()
        
        levels_stats[level]['total'] += student_count
    
    context = {
        'academic_year': academic_year,
        'previous_year': previous_year,
        'levels_stats': levels_stats,
        'total_students': sum(level['total'] for level in levels_stats.values()),
    }
    
    return render(request, 'belletin/admin/promote_students.html', context)

def get_next_level(current_level):
    """Obtient le niveau suivant pour la promotion"""
    levels = {
        'L1': 'L2',
        'L2': 'L3',
        'L3': 'M1',
        'M1': 'M2',
        'M2': 'M2'  # Pas de niveau supérieur
    }
    return levels.get(current_level, current_level)

def process_student_promotions(level, previous_year, new_year, stats):
    """
    Traite les promotions des étudiants d'un niveau spécifique
    
    Args:
        level: Le niveau actuel des étudiants (L1, L2, etc.)
        previous_year: L'année académique précédente
        new_year: La nouvelle année académique
        stats: Dictionnaire de statistiques à mettre à jour
    """
    # Récupérer tous les étudiants du niveau spécifié
    promotions = Promotion.objects.filter(level=level)
    students = Student.objects.filter(
        promotion__in=promotions,
        current_academic_year=previous_year
    ).select_related('user', 'promotion', 'promotion__department')
    
    stats['total_students'] += students.count()
    
    for student in students:
        # Trouver les délibérations de l'étudiant pour l'année précédente
        deliberations = StudentDeliberation.objects.filter(
            student=student,
            deliberation__academic_year=previous_year,
            deliberation__status='COMPLETED'
        ).select_related('deliberation')
        
        # Si pas de délibération, on ne peut pas promouvoir l'étudiant
        if not deliberations.exists():
            continue
        
        # Calculer les crédits totaux et la moyenne
        total_credits = 0
        total_points = 0
        credits_weight = 0
        
        for delib in deliberations:
            total_credits += delib.credits_obtained
            
            # Pour la moyenne pondérée
            if delib.average and delib.credits_obtained:
                total_points += delib.average * delib.credits_obtained
                credits_weight += delib.credits_obtained
        
        # Calculer la moyenne annuelle
        annual_average = total_points / credits_weight if credits_weight > 0 else 0
        
        # Déterminer la décision selon les critères LMD
        decision, explanation = determine_auto_decision(total_credits, annual_average)
        
        # Trouver la promotion de destination
        next_level = get_next_level(student.promotion.level)
        destination_promotion = Promotion.objects.filter(
            department=student.promotion.department,
            level=next_level
        ).first()
        
        # Si pas de promotion de destination, ne pas promouvoir
        if not destination_promotion and decision == 'ADMITTED':
            decision = 'FAILED'
            explanation = "Pas de niveau supérieur disponible"
        
        # Enregistrer la décision
        if decision == 'ADMITTED':
            # Promouvoir l'étudiant
            old_promotion = student.promotion
            student.promotion = destination_promotion
            student.current_academic_year = new_year
            student.save()
            
            # Enregistrer l'historique
            PromotionHistory.objects.create(
                student=student,
                from_promotion=old_promotion,
                to_promotion=destination_promotion,
                academic_year=new_year,
                decision=decision,
                comments=explanation,
                credits_obtained=total_credits,
                average=annual_average
            )
            
            stats['promoted'] += 1
        elif decision == 'REMEDIAL':
            # L'étudiant va en rattrapage mais reste au même niveau
            student.current_academic_year = new_year
            student.save()
            
            # Enregistrer l'historique
            PromotionHistory.objects.create(
                student=student,
                from_promotion=student.promotion,
                to_promotion=student.promotion, # Même promotion
                academic_year=new_year,
                decision=decision,
                comments=explanation,
                credits_obtained=total_credits,
                average=annual_average
            )
            
            stats['remedial'] += 1
        else: # FAILED
            # L'étudiant redouble, il reste au même niveau
            student.current_academic_year = new_year
            student.save()
            
            # Enregistrer l'historique
            PromotionHistory.objects.create(
                student=student,
                from_promotion=student.promotion,
                to_promotion=student.promotion, # Même promotion
                academic_year=new_year,
                decision=decision,
                comments=explanation,
                credits_obtained=total_credits,
                average=annual_average
            )
            
            stats['failed'] += 1
        
        stats['processed'] += 1

@login_required
def admin_dashboard(request):
    """Tableau de bord administrateur avec menu latéral"""
    # Vérifier que l'utilisateur est administrateur
    if not request.user.is_staff:
        messages.error(request, "Accès non autorisé. Vous n'êtes pas administrateur.")
        return redirect('belletin:dashboard')
    
    # Récupérer les statistiques pour le dashboard
    context = {
        'students_count': Student.objects.count(),
        'faculties_count': Faculty.objects.count(),
        'departments_count': Department.objects.count(),
        'current_year': AcademicYear.objects.filter(is_current=True).first()
    }
    
    return render(request, 'belletin/admin/dashboard.html', context)

# Vue pour la page hors ligne (offline)
def offline_view(request):
    """Vue simple pour afficher la page hors ligne"""
    return render(request, 'offline.html')