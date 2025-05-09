import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coupon.settings')
django.setup()

from belletin.models import Grade, UE, Student, AcademicYear, Promotion, Deliberation, StudentDeliberation
from django.db.models import Sum, Avg, F, ExpressionWrapper, FloatField

def update_bulletin_view_file():
    """
    Update the student_download_bulletin_coupon view function in views.py
    This will ensure the bulletin template shows LMD-compliant calculations
    """
    views_path = os.path.join('belletin', 'views.py')
    
    # Read the current views.py file
    with open(views_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the student_download_bulletin_coupon function
    start_keyword = "@login_required\ndef student_download_bulletin_coupon(request, deliberation_id):"
    if start_keyword not in content:
        print("Could not find student_download_bulletin_coupon function in views.py")
        return
    
    # Define the updated function code with proper escaping
    updated_function = '''@login_required
def student_download_bulletin_coupon(request, deliberation_id):
    """Télécharger le relevé de notes avec bulletin"""
    # Vérifier si l'utilisateur est un étudiant
    try:
        student = request.user.student
    except Student.DoesNotExist:
        messages.error(request, "Accès non autorisé. Vous n'êtes pas un étudiant.")
        return redirect('belletin:dashboard')
    
    # Obtenir la délibération
    deliberation = get_object_or_404(Deliberation, id=deliberation_id)
    
    # Vérifier que la délibération concerne la promotion de l'étudiant
    if deliberation.promotion != student.promotion:
        messages.error(request, "Vous n'êtes pas autorisé à accéder à ce relevé.")
        return redirect('belletin:student_bulletin')
    
    # Obtenir la décision pour cet étudiant
    student_deliberation = get_object_or_404(
        StudentDeliberation, 
        deliberation=deliberation,
        student=student,
        validated=True  # S'assurer que la décision a été validée
    )
    
    # Obtenir toutes les notes de l'étudiant
    grades = Grade.objects.filter(
        student=student
    ).select_related('ue')
    
    # Obtenir les UEs pour le semestre en cours
    ues = UE.objects.filter(
        promotion=student.promotion,
        semester=deliberation.semester
    )
    
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
    else:
        semester1_average = 0
    
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
    else:
        semester2_average = 0
    
    # Calcul des statistiques annuelles
    total_points = semester1_points + semester2_points
    total_credits = semester1_credits_total + semester2_credits_total
    total_credits_obtained = semester1_credits_obtained + semester2_credits_obtained
    credits_to_complete = total_credits - total_credits_obtained
    
    if total_credits > 0:
        annual_average = total_points / total_credits
    else:
        annual_average = 0
    
    # Points sur 1200 (60 crédits * 20 points max)
    max_points = total_credits * 20
    
    # Rendre le template avec les données calculées
    context = {
        'student': student,
        'deliberation': deliberation,
        'student_deliberation': student_deliberation,
        'grades': grades,
        'date': datetime.datetime.now(),
        'semester1_average': semester1_average,
        'semester1_credits': semester1_credits_obtained,
        'semester2_average': semester2_average,
        'semester2_credits': semester2_credits_obtained,
        'total_points': total_points,
        'max_points': max_points,
        'credits_to_complete': credits_to_complete
    }
    
    # Render HTML to PDF using WeasyPrint
    html_string = render_to_string('student/bulletin_coupon.html', context)
    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
    pdf = html.write_pdf()
    
    # Create HTTP response with PDF
    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f"bulletin_{student.matricule}_{deliberation.semester}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response'''
    
    # Replace the function in the content
    end_index = content.find("@login_required", content.find(start_keyword) + len(start_keyword))
    if end_index == -1:
        end_index = len(content)
    
    new_content = content[:content.find(start_keyword)] + updated_function + content[end_index:]
    
    # Create a backup of the original file
    backup_path = views_path + '.bak'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Created backup of original views.py at {backup_path}")
    
    # Write the updated content
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Successfully updated student_download_bulletin_coupon function in views.py")

if __name__ == "__main__":
    update_bulletin_view_file() 