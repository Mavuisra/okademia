from django import forms
from .models import (
    Student, Grade, UE, AnnualReport, Faculty, Department, Promotion, 
    Course, GradeComponent, Deliberation, StudentDeliberation, DeliberationChangeLog
)
from django.utils import timezone
from django.contrib.auth.models import User

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['user', 'matricule', 'promotion']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['promotion'].widget.attrs.update({'class': 'form-control'})
        self.fields['matricule'].widget.attrs.update({'class': 'form-control'})

class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = ['cc', 'mc']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cc'].widget.attrs.update({'class': 'form-control'})
        self.fields['mc'].widget.attrs.update({'class': 'form-control'})

class UEForm(forms.ModelForm):
    class Meta:
        model = UE
        fields = '__all__'

class FacultyForm(forms.ModelForm):
    class Meta:
        model = Faculty
        fields = ['name']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'form-control'})

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'faculty']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class PromotionForm(forms.ModelForm):
    class Meta:
        model = Promotion
        fields = ['level', 'department', 'academic_year']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class QuickGradeForm(forms.Form):
    tp = forms.FloatField(
        min_value=0, max_value=5,
        widget=forms.NumberInput(attrs={'step': '0.5', 'class': 'form-control'})
    )
    interrogation = forms.FloatField(
        min_value=0, max_value=5,
        widget=forms.NumberInput(attrs={'step': '0.5', 'class': 'form-control'})
    )
    examen = forms.FloatField(
        min_value=0, max_value=10,
        widget=forms.NumberInput(attrs={'step': '0.5', 'class': 'form-control'})
    )

# Nouveaux formulaires pour les jurys et délibérations

class DeliberationCreateForm(forms.ModelForm):
    class Meta:
        model = Deliberation
        fields = ['promotion', 'semester', 'academic_year', 'date_scheduled']
        widgets = {
            'date_scheduled': forms.DateTimeInput(attrs={'type': 'datetime-local'})
        }

class DeliberationFilterForm(forms.Form):
    faculty = forms.ModelChoiceField(
        queryset=Faculty.objects.all(),
        required=False,
        empty_label="Toutes les facultés",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        empty_label="Tous les départements",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    promotion_level = forms.ChoiceField(
        choices=[('', 'Tous les niveaux')] + Promotion.LEVEL_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    semester = forms.ChoiceField(
        choices=[('', 'Tous les semestres')] + UE.SEMESTER_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=[('', 'Tous les statuts')] + Deliberation.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class StudentDeliberationDecisionForm(forms.ModelForm):
    class Meta:
        model = StudentDeliberation
        fields = ['final_decision', 'comments']
        widgets = {
            'comments': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'})
        }

class StudentDeliberationBulkForm(forms.Form):
    students = forms.ModelMultipleChoiceField(
        queryset=Student.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    decision = forms.ChoiceField(
        choices=StudentDeliberation.DECISION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=True
    )

    def __init__(self, *args, **kwargs):
        deliberation_token = kwargs.pop('deliberation_token', None)
        deliberation_id = kwargs.pop('deliberation_id', None)
        super().__init__(*args, **kwargs)
        
        if deliberation_token:
            deliberation = Deliberation.objects.get(token=deliberation_token)
            self.fields['students'].queryset = Student.objects.filter(
                promotion=deliberation.promotion
            )
        elif deliberation_id:
            deliberation = Deliberation.objects.get(id=deliberation_id)
            self.fields['students'].queryset = Student.objects.filter(
                promotion=deliberation.promotion
            )

class DeliberationChangeLogForm(forms.ModelForm):
    class Meta:
        model = DeliberationChangeLog
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'})
        } 