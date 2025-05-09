from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import datetime, timedelta

class AcademicYear(models.Model):
    """Année académique"""
    # Anciens champs
    year = models.DateField(null=True, blank=True)  # Obsolète, à supprimer plus tard
    
    # Nouveaux champs
    name = models.CharField(max_length=100, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    
    def __str__(self):
        if self.name:
            return self.name
        elif self.year:
            return f"{self.year.year}-{self.year.year + 1}"
        return "Année non définie"
    
    def save(self, *args, **kwargs):
        if self.is_current:
            # Mettre à jour les autres années académiques
            AcademicYear.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

class Faculty(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name

class Department(models.Model):
    name = models.CharField(max_length=100)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.name} ({self.faculty})"

class Promotion(models.Model):
    LEVEL_CHOICES = [('L1', 'Licence 1'), ('L2', 'Licence 2'), ('L3', 'Licence 3')]
    
    level = models.CharField(max_length=2, choices=LEVEL_CHOICES)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.get_level_display()} - {self.department} ({self.academic_year})"

class Student(models.Model):
    """Profil étudiant"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    matricule = models.CharField(max_length=50, unique=True)
    promotion = models.ForeignKey('Promotion', on_delete=models.CASCADE)
    current_academic_year = models.ForeignKey('AcademicYear', related_name='current_students', 
                                             on_delete=models.SET_NULL, null=True, blank=True)
    admission_year = models.ForeignKey('AcademicYear', related_name='admitted_students',
                                      on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} ({self.matricule})"

class UE(models.Model):
    SEMESTER_CHOICES = [(1, "Semestre 1"), (2, "Semestre 2")]
    
    code = models.CharField(max_length=20)
    title = models.CharField(max_length=200)
    credits = models.PositiveIntegerField()
    semester = models.PositiveIntegerField(choices=SEMESTER_CHOICES)
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE)
    is_group = models.BooleanField(default=False)
    parent_ue = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.code} - {self.title}"

class Grade(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    ue = models.ForeignKey(UE, on_delete=models.CASCADE)
    cc = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(20)]
    )
    mc = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(20)]
    )
    moyenne = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(20)]
    )
    resultat = models.CharField(max_length=50, default='NON VALIDÉ')
    
    class Meta:
        unique_together = ('student', 'ue')
        
    def save(self, *args, **kwargs):
        # Calculer la moyenne si cc et mc sont définis
        if self.cc is not None and self.mc is not None:
            self.moyenne = (self.cc + self.mc) / 2
            # Déterminer le résultat
            self.resultat = 'VALIDÉ' if self.moyenne >= 10 else 'NON VALIDÉ'
        
        super().save(*args, **kwargs)

class AnnualReport(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    total_credits = models.PositiveIntegerField()
    annual_average = models.FloatField()
    appreciation = models.CharField(max_length=50)
    
    def __str__(self):
        return f"Rapport {self.academic_year} - {self.student}"

class Professor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()}"

class Course(models.Model):
    ue = models.ForeignKey(UE, on_delete=models.CASCADE)
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    deadline = models.DateField(null=True, blank=True)
    
    class Meta:
        unique_together = ('ue', 'professor', 'academic_year')
    
    def __str__(self):
        return f"{self.ue} - {self.professor}"

class GradeComponent(models.Model):
    COMPONENT_TYPES = [
        ('TP', 'Travaux Pratiques'),
        ('CC', 'Contrôle Continu'),
        ('EX', 'Examen')
    ]
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    type = models.CharField(max_length=2, choices=COMPONENT_TYPES)
    score = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(20)],
        null=True, blank=True
    )
    date_added = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('course', 'student', 'type')

class GradeModificationLog(models.Model):
    component = models.ForeignKey(GradeComponent, on_delete=models.CASCADE)
    old_value = models.FloatField(null=True)
    new_value = models.FloatField(null=True)
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    modified_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True)

    def __str__(self):
        return f"Modification de note pour {self.component.student} par {self.modified_by}"

# Nouveaux modèles pour le jury et les délibérations

class JuryMember(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    promotions = models.ManyToManyField(Promotion, related_name='jury_members')
    is_president = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {'Président' if self.is_president else 'Membre'}"

class Deliberation(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('IN_PROGRESS', 'En cours'),
        ('COMPLETED', 'Terminée')
    ]
    
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE)
    semester = models.PositiveIntegerField(choices=UE.SEMESTER_CHOICES)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    date_scheduled = models.DateTimeField()
    date_completed = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    token = models.CharField(max_length=500, blank=True, null=True, unique=True, db_index=True)
    
    def __str__(self):
        return f"Délibération {self.promotion} - S{self.semester} ({self.academic_year})"
    
    def save(self, *args, **kwargs):
        creating = self._state.adding
        # Conserver l'ancien token pour vérification
        old_token = None if creating else Deliberation.objects.filter(pk=self.pk).values_list('token', flat=True).first()
        
        # Générer un token seulement si nécessaire
        if not self.token or old_token != self.token:
            from .utils import encode_id
            # Utiliser l'ID actuel ou un ID temporaire si c'est une nouvelle instance
            temp_id = self.id if self.id else 0
            self.token = encode_id(temp_id, 'Deliberation')
        
        # Sauvegarder l'instance
        super().save(*args, **kwargs)
        
        # Si c'est une création ou si le token était basé sur ID=0, mettre à jour avec l'ID réel
        if creating or (self.token and 'id":0' in self.token):
            from .utils import encode_id
            # Générer un nouveau token avec l'ID correct
            self.token = encode_id(self.id, 'Deliberation')
            # Sauvegarder à nouveau
            update_fields = kwargs.get('update_fields', None)
            if update_fields:
                if 'token' not in update_fields:
                    update_fields.append('token')
            else:
                kwargs['update_fields'] = ['token']
            
            # Utiliser update() direct pour éviter une récursion
            Deliberation.objects.filter(pk=self.pk).update(token=self.token)
    
    class Meta:
        unique_together = ('promotion', 'semester', 'academic_year')

class DeliberationMember(models.Model):
    deliberation = models.ForeignKey(Deliberation, on_delete=models.CASCADE)
    jury_member = models.ForeignKey(JuryMember, on_delete=models.CASCADE)
    is_present = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('deliberation', 'jury_member')

class StudentDeliberation(models.Model):
    DECISION_CHOICES = [
        ('ADMITTED', 'Admis'),
        ('REMEDIAL', 'Rattrapage'),
        ('FAILED', 'Ajourné')
    ]
    
    deliberation = models.ForeignKey(Deliberation, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    average = models.FloatField(default=0)
    credits_obtained = models.PositiveIntegerField(default=0)
    auto_decision = models.CharField(max_length=20, choices=DECISION_CHOICES)
    final_decision = models.CharField(max_length=20, choices=DECISION_CHOICES, null=True, blank=True)
    validated = models.BooleanField(default=False)
    validated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    comments = models.TextField(blank=True)
    token = models.CharField(max_length=500, blank=True, null=True, unique=True, db_index=True)
    
    class Meta:
        unique_together = ('deliberation', 'student')
    
    def __str__(self):
        return f"Délibération de {self.student} - {self.get_final_decision_display() or self.get_auto_decision_display()}"
    
    def save(self, *args, **kwargs):
        creating = self._state.adding
        # Conserver l'ancien token pour vérification
        old_token = None if creating else StudentDeliberation.objects.filter(pk=self.pk).values_list('token', flat=True).first()
        
        # Générer un token seulement si nécessaire
        if not self.token or old_token != self.token:
            from .utils import encode_id
            # Utiliser l'ID actuel ou un ID temporaire si c'est une nouvelle instance
            temp_id = self.id if self.id else 0
            self.token = encode_id(temp_id, 'StudentDeliberation')
        
        # Sauvegarder l'instance
        super().save(*args, **kwargs)
        
        # Si c'est une création ou si le token était basé sur ID=0, mettre à jour avec l'ID réel
        if creating or (self.token and 'id":0' in self.token):
            from .utils import encode_id
            # Générer un nouveau token avec l'ID correct
            self.token = encode_id(self.id, 'StudentDeliberation')
            # Sauvegarder à nouveau
            update_fields = kwargs.get('update_fields', None)
            if update_fields:
                if 'token' not in update_fields:
                    update_fields.append('token')
            else:
                kwargs['update_fields'] = ['token']
            
            # Utiliser update() direct pour éviter une récursion
            StudentDeliberation.objects.filter(pk=self.pk).update(token=self.token)

class DeliberationChangeLog(models.Model):
    student_deliberation = models.ForeignKey(StudentDeliberation, on_delete=models.CASCADE)
    previous_decision = models.CharField(max_length=20, choices=StudentDeliberation.DECISION_CHOICES)
    new_decision = models.CharField(max_length=20, choices=StudentDeliberation.DECISION_CHOICES)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField()
    
    def __str__(self):
        return f"Modification de {self.previous_decision} à {self.new_decision} pour {self.student_deliberation.student}"

class PromotionHistory(models.Model):
    """Historique des promotions d'un étudiant"""
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='promotion_history')
    from_promotion = models.ForeignKey('Promotion', on_delete=models.CASCADE, related_name='from_histories')
    to_promotion = models.ForeignKey('Promotion', on_delete=models.CASCADE, related_name='to_histories')
    academic_year = models.ForeignKey('AcademicYear', on_delete=models.CASCADE)
    promoted_at = models.DateTimeField(auto_now_add=True)
    decision = models.CharField(max_length=20, choices=[
        ('ADMITTED', 'Admis(e)'),
        ('REMEDIAL', 'Rattrapage'),
        ('FAILED', 'Ajourné(e)')
    ])
    comments = models.TextField(blank=True, null=True)
    credits_obtained = models.IntegerField(default=0)
    average = models.FloatField(default=0)
    
    def __str__(self):
        return f"{self.student.matricule} - {self.from_promotion} à {self.to_promotion} ({self.academic_year})"

# Modèles pour les notifications push
class PushSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.TextField()
    p256dh = models.TextField()
    auth = models.TextField()
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'endpoint')
        verbose_name = "Abonnement aux notifications push"
        verbose_name_plural = "Abonnements aux notifications push"
    
    def __str__(self):
        return f"Abonnement Push de {self.user.username}"

class NotificationPreference(models.Model):
    NOTIFICATION_TYPES = (
        ('grades', 'Notes'),
        ('deliberations', 'Délibérations'),
        ('announcements', 'Annonces'),
        ('calendar', 'Calendrier'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_preferences')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    enabled = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('user', 'notification_type')
        verbose_name = "Préférence de notification"
        verbose_name_plural = "Préférences de notification"
    
    def __str__(self):
        return f"{self.get_notification_type_display()} pour {self.user.username}: {'activé' if self.enabled else 'désactivé'}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    url = models.URLField(blank=True, null=True)
    icon = models.CharField(max_length=255, blank=True, null=True)
    notification_type = models.CharField(max_length=50)
    read = models.BooleanField(default=False)
    sent_push = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
    
    def __str__(self):
        return f"{self.title} pour {self.user.username}"
    
    def mark_as_read(self):
        self.read = True
        self.save()
        
    def send_push(self):
        if self.sent_push:
            return
            
        from .utils.push_notifications import send_push_notification
        
        # Vérifier les préférences de l'utilisateur
        try:
            pref = NotificationPreference.objects.get(
                user=self.user, 
                notification_type=self.notification_type
            )
            if not pref.enabled:
                return
        except NotificationPreference.DoesNotExist:
            # Si aucune préférence n'existe, on suppose que les notifications sont activées
            pass
            
        # Récupérer les abonnements push de l'utilisateur
        subscriptions = PushSubscription.objects.filter(user=self.user)
        
        for subscription in subscriptions:
            payload = {
                'title': self.title,
                'body': self.message,
                'icon': self.icon or '/static/pwa/icons/icon-192x192.svg',
                'badge': '/static/pwa/icons/notification-badge.svg',
                'vibrate': [100, 50, 100],
                'data': {
                    'url': self.url or '/',
                    'notificationId': self.id
                }
            }
            
            subscription_info = {
                'endpoint': subscription.endpoint,
                'keys': {
                    'p256dh': subscription.p256dh,
                    'auth': subscription.auth
                }
            }
            
            try:
                send_push_notification(subscription_info, payload)
                self.sent_push = True
                self.save()
            except Exception as e:
                # En cas d'erreur, on peut supposer que l'abonnement est invalide
                print(f"Erreur lors de l'envoi de la notification push: {e}")
                
                # Si l'erreur indique que l'abonnement n'est plus valide, on peut le supprimer
                if "push subscription has unsubscribed or expired" in str(e):
                    subscription.delete()

class OfflineQueue(models.Model):
    """
    File d'attente pour les opérations effectuées hors ligne
    à synchroniser ultérieurement lorsque la connexion est rétablie.
    """
    OPERATION_TYPES = (
        ('CREATE', 'Création'),
        ('UPDATE', 'Mise à jour'),
        ('DELETE', 'Suppression'),
    )
    
    STATUS_CHOICES = (
        ('PENDING', 'En attente'),
        ('PROCESSING', 'En cours'),
        ('COMPLETED', 'Terminé'),
        ('FAILED', 'Échoué'),
    )
    
    # Identification de l'opération
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    operation_type = models.CharField(max_length=10, choices=OPERATION_TYPES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    
    # Données de l'opération
    data = models.JSONField(default=dict)
    
    # État de la synchronisation
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    retry_count = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'File d\'attente hors ligne'
        verbose_name_plural = 'Files d\'attente hors ligne'
    
    def __str__(self):
        return f"{self.operation_type} - {self.model_name} - {self.status}"
