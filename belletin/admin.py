from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import path
from django.shortcuts import redirect
from .views import admin_new_academic_year
from .models import (
    Faculty, Department, Professor, Student,
    AcademicYear, Promotion, UE, Grade,
    Course, GradeComponent, GradeModificationLog,
    JuryMember, Deliberation, StudentDeliberation, 
    DeliberationMember, DeliberationChangeLog,
    OfflineQueue
)

# Création d'une nouvelle instance de CustomAdminSite
class CustomAdminSite(admin.AdminSite):
    site_header = 'Système de Gestion Académique SYGAC'
    site_title = 'SYGAC Admin'
    index_title = 'Tableau de Bord SYGAC'

    def each_context(self, request):
        context = super().each_context(request)
        context['custom_css'] = '''
            :root {
                --primary: #1e3c72;
                --secondary: #2a5298;
            }
            
            #header {
                background: linear-gradient(135deg, var(--primary), var(--secondary));
                color: white !important;
            }
            
            #header a:link, #header a:visited {
                color: white !important;
            }
            
            #branding h1 {
                color: white !important;
            }
            
            .module h2, .module caption, .inline-group h2 {
                background: var(--primary) !important;
                color: white !important;
            }
            
            div.breadcrumbs {
                background: var(--secondary) !important;
                color: white !important;
            }
            
            div.breadcrumbs a {
                color: white !important;
            }
            
            .button, input[type=submit], input[type=button], .submit-row input, a.button {
                background: var(--primary) !important;
                color: white !important;
            }
            
            .button:hover, input[type=submit]:hover, input[type=button]:hover {
                background: var(--secondary) !important;
            }
            
            .button.default, input[type=submit].default {
                background: var(--primary) !important;
            }
            
            .button.default:hover, input[type=submit].default:hover {
                background: var(--secondary) !important;
            }
        '''
        return context
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('new-academic-year/', self.admin_view(admin_new_academic_year), name='new-academic-year'),
        ]
        return custom_urls + urls

# Création de l'instance du site admin personnalisé
admin_site = CustomAdminSite(name='admin')

# Personnalisation de l'admin des utilisateurs
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_groups')
    list_filter = ('is_staff', 'is_superuser', 'groups')
    
    def get_groups(self, obj):
        return ", ".join([group.name for group in obj.groups.all()])
    get_groups.short_description = 'Rôles'

# Personnalisation de l'admin des groupes
class CustomGroupAdmin(GroupAdmin):
    list_display = ('name', 'get_permissions')
    
    def get_permissions(self, obj):
        return ", ".join([perm.codename for perm in obj.permissions.all()])
    get_permissions.short_description = 'Permissions'

# Inline pour les cours d'un professeur
class CourseInline(admin.TabularInline):
    model = Course
    extra = 1

# Admin pour Professeur
class ProfessorAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'get_full_name', 'get_email')
    list_filter = ('department',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    inlines = [CourseInline]

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Nom complet'

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Ajouter l'utilisateur au groupe Professeur
        professor_group, _ = Group.objects.get_or_create(name='Professeur')
        obj.user.groups.add(professor_group)

# Admin pour Étudiant avec gestion automatique des rôles
class StudentAdmin(admin.ModelAdmin):
    list_display = ('matricule', 'user', 'get_full_name', 'promotion')
    list_filter = ('promotion',)
    search_fields = ('matricule', 'user__username', 'user__first_name', 'user__last_name')

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Nom complet'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Ajouter l'utilisateur au groupe Étudiant
        student_group, _ = Group.objects.get_or_create(name='Étudiant')
        obj.user.groups.add(student_group)

# Autres classes Admin...
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'faculty')
    list_filter = ('faculty',)
    search_fields = ('name', 'faculty__name')

class FacultyAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_current')
    list_filter = ('is_current',)
    search_fields = ('name',)
    list_editable = ('is_current',)

class PromotionAdmin(admin.ModelAdmin):
    list_display = ('level', 'department', 'academic_year')
    list_filter = ('level', 'department', 'academic_year')
    search_fields = ('department__name',)

class UEAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'credits', 'semester', 'promotion')
    list_filter = ('semester', 'promotion', 'is_group')
    search_fields = ('code', 'title')

class GradeAdmin(admin.ModelAdmin):
    list_display = ('student', 'ue', 'cc', 'mc')
    list_filter = ('ue', 'student__promotion')
    search_fields = ('student__user__username', 'student__matricule', 'ue__code')

class GradeComponentAdmin(admin.ModelAdmin):
    list_display = ('course', 'student', 'type', 'score', 'date_added')
    list_filter = ('type', 'course', 'date_added')
    search_fields = ('student__user__username', 'course__ue__code')

class GradeModificationLogAdmin(admin.ModelAdmin):
    list_display = ('component', 'old_value', 'new_value', 'modified_by', 'modified_at')
    list_filter = ('modified_at', 'modified_by')
    search_fields = ('component__student__user__username', 'modified_by__username')
    readonly_fields = ('modified_at',)

class JuryMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_full_name', 'is_president', 'get_promotions')
    list_filter = ('is_president', 'promotions')
    filter_horizontal = ('promotions',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Nom complet'

    def get_promotions(self, obj):
        return ", ".join([promo.get_level_display() for promo in obj.promotions.all()])
    get_promotions.short_description = 'Promotions'
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Ajouter l'utilisateur au groupe Jury
        jury_group, _ = Group.objects.get_or_create(name='Jury')
        obj.user.groups.add(jury_group)

class DeliberationMemberInline(admin.TabularInline):
    model = DeliberationMember
    extra = 1

class StudentDeliberationInline(admin.TabularInline):
    model = StudentDeliberation
    extra = 0
    fields = ('student', 'average', 'credits_obtained', 'auto_decision', 'final_decision', 'validated')
    readonly_fields = ('auto_decision',)

class DeliberationAdmin(admin.ModelAdmin):
    list_display = ('promotion', 'semester', 'academic_year', 'date_scheduled', 'status')
    list_filter = ('status', 'semester', 'academic_year', 'promotion__department')
    search_fields = ('promotion__department__name',)
    inlines = [DeliberationMemberInline, StudentDeliberationInline]

class StudentDeliberationAdmin(admin.ModelAdmin):
    list_display = ('student', 'deliberation', 'average', 'credits_obtained', 'auto_decision', 'final_decision', 'validated')
    list_filter = ('validated', 'auto_decision', 'final_decision', 'deliberation')
    search_fields = ('student__matricule', 'student__user__first_name', 'student__user__last_name')
    readonly_fields = ('auto_decision',)

class DeliberationChangeLogAdmin(admin.ModelAdmin):
    list_display = ('student_deliberation', 'previous_decision', 'new_decision', 'changed_by', 'changed_at')
    list_filter = ('previous_decision', 'new_decision', 'changed_at')
    search_fields = ('student_deliberation__student__matricule', 'changed_by__username')
    readonly_fields = ('changed_at',)

# Register OfflineQueue model
@admin.register(OfflineQueue)
class OfflineQueueAdmin(admin.ModelAdmin):
    list_display = ('operation_type', 'model_name', 'object_id', 'status', 'user', 'created_at')
    list_filter = ('operation_type', 'status', 'model_name')
    search_fields = ('model_name', 'object_id', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Opération', {
            'fields': ('operation_type', 'model_name', 'object_id', 'user')
        }),
        ('Données', {
            'fields': ('data',)
        }),
        ('État', {
            'fields': ('status', 'retry_count', 'error_message')
        }),
        ('Horodatage', {
            'fields': ('created_at', 'updated_at')
        }),
    )

# Enregistrement des modèles avec le site admin personnalisé
admin_site.register(User, CustomUserAdmin)
admin_site.register(Group, CustomGroupAdmin)
admin_site.register(Professor, ProfessorAdmin)
admin_site.register(Department, DepartmentAdmin)
admin_site.register(Faculty, FacultyAdmin)
admin_site.register(AcademicYear, AcademicYearAdmin)
admin_site.register(Promotion, PromotionAdmin)
admin_site.register(UE, UEAdmin)
admin_site.register(Grade, GradeAdmin)
admin_site.register(GradeComponent, GradeComponentAdmin)
admin_site.register(GradeModificationLog, GradeModificationLogAdmin)
admin_site.register(Student, StudentAdmin)
admin_site.register(JuryMember, JuryMemberAdmin)
admin_site.register(Deliberation, DeliberationAdmin)
admin_site.register(StudentDeliberation, StudentDeliberationAdmin)
admin_site.register(DeliberationChangeLog, DeliberationChangeLogAdmin)

# Création des groupes et permissions par défaut
def create_default_groups():
    # Groupe Admin
    admin_group, _ = Group.objects.get_or_create(name='Admin')
    admin_group.permissions.add(*Permission.objects.all())

    # Groupe Professeur
    professor_group, _ = Group.objects.get_or_create(name='Professeur')
    professor_permissions = [
        'view_course', 'add_course', 'change_course',
        'view_gradecomponent', 'add_gradecomponent', 'change_gradecomponent',
        'view_student', 'view_ue',
        'view_grade', 'add_grade', 'change_grade'
    ]
    for codename in professor_permissions:
        for content_type in ContentType.objects.all():
            try:
                perm = Permission.objects.get(codename=codename, content_type=content_type)    
                professor_group.permissions.add(perm)
            except Permission.DoesNotExist:
                continue

    # Groupe Jury
    jury_group, _ = Group.objects.get_or_create(name='Jury')
    jury_permissions = [
        'view_deliberation', 'add_deliberation', 'change_deliberation',
        'view_studentdeliberation', 'add_studentdeliberation', 'change_studentdeliberation',
        'view_deliberationchangelog', 'add_deliberationchangelog',
        'view_student', 'view_grade', 'view_ue'
    ]
    for codename in jury_permissions:
        for content_type in ContentType.objects.all():
            try:
                perm = Permission.objects.get(codename=codename, content_type=content_type)
                jury_group.permissions.add(perm)
            except Permission.DoesNotExist:
                continue

    # Groupe Étudiant
    student_group, _ = Group.objects.get_or_create(name='Étudiant')
    student_permissions = [
        'view_grade', 'view_ue', 'view_course', 'view_studentdeliberation'
    ]
    for codename in student_permissions:
        for content_type in ContentType.objects.all():
            try:
                perm = Permission.objects.get(codename=codename, content_type=content_type)    
                student_group.permissions.add(perm)
            except Permission.DoesNotExist:
                continue
