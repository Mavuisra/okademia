import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coupon.settings')
django.setup()

from belletin.models import Grade, UE, Student, AcademicYear

# Get semester 2 UEs
ues = UE.objects.filter(semester=2)
students = Student.objects.all()
current_year = AcademicYear.objects.first()

if not ues.exists():
    print("No UEs found for semester 2")
    sys.exit(1)

if not students.exists():
    print("No students found")
    sys.exit(1)

print(f"Found {ues.count()} UEs for semester 2")
print(f"Found {students.count()} students")

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

print(f"Created {count} grades for semester 2") 