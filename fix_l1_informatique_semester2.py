import os
import sys
import django
import datetime

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coupon.settings')
django.setup()

from belletin.models import Grade, UE, Student, AcademicYear, Promotion, Department, Faculty, Deliberation, StudentDeliberation
from django.db.models import Q

# Get the academic year (use the ID or date directly)
academic_year = AcademicYear.objects.get(id=1)  # Based on our query result
print(f"Using academic year: {academic_year.year}")

# Find the department
department = Department.objects.filter(name__icontains="Informatique").first()
if not department:
    print("Informatique department not found")
    sys.exit(1)

# Find the promotion (L1)
promotion = Promotion.objects.get(id=1)  # Based on our query result
print(f"Found promotion: {promotion}")

# Get all UEs for this promotion with semester 2
ues = UE.objects.filter(promotion=promotion, semester=2)
if not ues.exists():
    print("No semester 2 UEs found for this promotion")
    sys.exit(1)

print(f"Found {ues.count()} UEs for semester 2 in {promotion}")

# Get all students in this promotion
students = Student.objects.filter(promotion=promotion)
if not students.exists():
    print("No students found in this promotion")
    sys.exit(1)

print(f"Found {students.count()} students in {promotion}")

# Create grades for each student for each UE
count = 0
for student in students:
    for ue in ues:
        # Check if grade already exists
        if not Grade.objects.filter(student=student, ue=ue).exists():
            Grade.objects.create(
                student=student,
                ue=ue,
                cc=14,  # Example grade
                mc=16,  # Example grade
            )
            count += 1

print(f"Created {count} grades for semester 2 in {promotion}")

# Check if there are existing deliberations for this promotion and semester
deliberation = Deliberation.objects.filter(
    promotion=promotion,
    semester=2,
    academic_year=academic_year
).first()

if not deliberation:
    print("Creating new deliberation for semester 2")
    deliberation = Deliberation.objects.create(
        promotion=promotion,
        semester=2,
        academic_year=academic_year,
        date_scheduled=datetime.datetime.now(),
        status='PENDING'
    )
    print(f"Created deliberation: {deliberation}")
else:
    print(f"Found existing deliberation: {deliberation}")

# Check if student deliberations exist
student_deliberations = StudentDeliberation.objects.filter(deliberation=deliberation)
print(f"Found {student_deliberations.count()} student deliberations")

# If no student deliberations exist, create them
if student_deliberations.count() == 0:
    print("Creating student deliberations")
    for student in students:
        # Calculate averages and credits
        student_grades = Grade.objects.filter(
            student=student,
            ue__in=ues
        )
        
        # Calculate average
        total_points = 0
        total_credits = 0
        credits_obtained = 0
        
        for grade in student_grades:
            if grade.cc is not None and grade.mc is not None:
                ue_average = (grade.cc + grade.mc) / 2
                total_points += ue_average * grade.ue.credits
                total_credits += grade.ue.credits
                
                # Student gets credits if average >= 10
                if ue_average >= 10:
                    credits_obtained += grade.ue.credits
        
        average = total_points / total_credits if total_credits > 0 else 0
        
        # Determine automatic decision
        if average >= 10 and credits_obtained == total_credits:
            auto_decision = 'ADMITTED'
        elif average >= 8:
            auto_decision = 'REMEDIAL'
        else:
            auto_decision = 'FAILED'
        
        # Create StudentDeliberation
        StudentDeliberation.objects.create(
            deliberation=deliberation,
            student=student,
            average=average,
            credits_obtained=credits_obtained,
            auto_decision=auto_decision
        )
        print(f"Created deliberation entry for student: {student}")

print("Finished setting up student deliberations") 