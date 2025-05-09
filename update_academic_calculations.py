import os
import sys
import django
import datetime

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coupon.settings')
django.setup()

from belletin.models import Grade, UE, Student, AcademicYear, Promotion, Deliberation, StudentDeliberation
from django.db.models import Sum, F, FloatField, ExpressionWrapper
from django.db.models.functions import Coalesce

def get_appreciation(average):
    """Return the appreciation based on average"""
    if average >= 16:
        return "Très Bien"
    elif average >= 14:
        return "Bien"
    elif average >= 12:
        return "Assez Bien"
    elif average >= 10:
        return "Passable"
    else:
        return "Insuffisant"

def calculate_semester_stats(student, semester, academic_year):
    """Calculate semester average and credits obtained"""
    # Get UEs for this semester
    ues = UE.objects.filter(
        promotion=student.promotion,
        semester=semester
    )
    
    if not ues.exists():
        return {
            'average': 0,
            'credits_obtained': 0,
            'total_points': 0,
            'max_points': 0,
            'total_credits': 0
        }
    
    # Get grades for these UEs
    grades = Grade.objects.filter(
        student=student,
        ue__in=ues
    ).select_related('ue')
    
    # Calculate average and credits
    total_points = 0
    total_credits = 0
    credits_obtained = 0
    
    for grade in grades:
        if grade.cc is not None and grade.mc is not None:
            # Calculate UE average (CC + MC) / 2
            ue_average = (grade.cc + grade.mc) / 2
            
            # Add weighted points to total
            total_points += ue_average * grade.ue.credits
            total_credits += grade.ue.credits
            
            # Add credits if UE is validated (average >= 10)
            if ue_average >= 10:
                credits_obtained += grade.ue.credits
    
    # Calculate semester average
    average = total_points / total_credits if total_credits > 0 else 0
    
    # Maximum possible points (20 per credit)
    max_points = total_credits * 20
    
    # Calculate percentage of success (total points / max possible points)
    percentage = (total_points / max_points * 100) if max_points > 0 else 0
    
    return {
        'average': average,
        'credits_obtained': credits_obtained,
        'total_points': total_points,
        'max_points': max_points,
        'total_credits': total_credits,
        'percentage': percentage
    }

def update_student_deliberation(deliberation):
    """Update student deliberations with correct calculations"""
    print(f"Updating calculations for {deliberation}")
    
    # Get all students in this deliberation
    student_deliberations = StudentDeliberation.objects.filter(
        deliberation=deliberation
    ).select_related('student', 'student__promotion')
    
    updated_count = 0
    for sd in student_deliberations:
        student = sd.student
        
        # Calculate stats for both semesters
        semester1_stats = calculate_semester_stats(student, 1, deliberation.academic_year)
        semester2_stats = calculate_semester_stats(student, 2, deliberation.academic_year)
        
        # Calculate annual average and total points
        total_credits_obtained = semester1_stats['credits_obtained'] + semester2_stats['credits_obtained']
        total_credits_available = semester1_stats['total_credits'] + semester2_stats['total_credits']
        annual_total_points = semester1_stats['total_points'] + semester2_stats['total_points']
        max_annual_points = semester1_stats['max_points'] + semester2_stats['max_points']
        
        # Annual average based on weighted semester averages
        if semester1_stats['total_credits'] > 0 or semester2_stats['total_credits'] > 0:
            # Correct weighted average calculation:
            # [(Moy S1 × Crédits S1) + (Moy S2 × Crédits S2)] / Total Crédits
            annual_average = annual_total_points / (semester1_stats['total_credits'] + semester2_stats['total_credits'])
        else:
            annual_average = 0
        
        # Calculate percentage of overall success (points obtained over maximum possible)
        # This is the correct LMD percentage calculation: total points / (total credits * 20) * 100
        success_percentage = (annual_total_points / max_annual_points * 100) if max_annual_points > 0 else 0
        
        # Calculate percentage of credits obtained
        credit_completion_percentage = (total_credits_obtained / total_credits_available * 100) if total_credits_available > 0 else 0
        
        # Determine auto decision based on new promotion rules
        # To move to next level: at least 45 credits out of 60 needed
        minimum_credits_for_promotion = 45
        
        if total_credits_obtained >= minimum_credits_for_promotion:
            # Student has enough credits to pass to next level
            if total_credits_obtained == total_credits_available:
                # All credits obtained (60/60)
                auto_decision = 'ADMITTED'
            else:
                # Passed but needs to retake failed courses in the next level
                auto_decision = 'ADMITTED'
        elif annual_average >= 8:  # Pass with remediation
            auto_decision = 'REMEDIAL'
        else:  # Failed
            auto_decision = 'FAILED'
        
        # Update StudentDeliberation object
        sd.average = annual_average
        sd.credits_obtained = total_credits_obtained
        sd.auto_decision = auto_decision
        sd.save()
        
        updated_count += 1
        print(f"Updated {student}: Avg={annual_average:.2f}, Credits={total_credits_obtained}/{total_credits_available} ({credit_completion_percentage:.1f}%), Decision={auto_decision}")
        print(f"  Points: {annual_total_points:.1f}/{max_annual_points} ({success_percentage:.1f}%), Appreciation: {get_appreciation(annual_average)}")
    
    print(f"Updated {updated_count} student deliberations")

def main():
    """Main function to update all deliberations or a specific one"""
    # Check if deliberation ID was provided
    if len(sys.argv) > 1:
        try:
            deliberation_id = int(sys.argv[1])
            deliberation = Deliberation.objects.get(id=deliberation_id)
            update_student_deliberation(deliberation)
        except (ValueError, Deliberation.DoesNotExist):
            print(f"Deliberation with ID {sys.argv[1]} not found")
            sys.exit(1)
    else:
        # Update all deliberations
        deliberations = Deliberation.objects.all()
        for deliberation in deliberations:
            update_student_deliberation(deliberation)

if __name__ == "__main__":
    main() 