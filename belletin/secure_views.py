from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from django.http import Http404

from .models import (
    Deliberation, Student, StudentDeliberation, DeliberationChangeLog,
    JuryMember, UE, Grade, Course, GradeComponent
)
from .forms import StudentDeliberationDecisionForm, StudentDeliberationBulkForm
from .utils import decode_id, resolve_deliberation_token

# Décorateur pour traiter les tokens de délibération
def with_decoded_deliberation(view_func):
    """Décorateur qui décode le token de délibération avant d'exécuter la vue."""
    def wrapper(request, deliberation_token, *args, **kwargs):
        try:
            # Stocker la requête pour accès dans le résolveur de token
            from .utils import resolve_deliberation_token
            setattr(resolve_deliberation_token, 'request', request)
            
            # Résoudre le token de délibération
            deliberation = resolve_deliberation_token(deliberation_token)
            
            # Si c'est pour les fonctions qui attendent l'objet délibération directement
            if view_func.__name__ in ['student_download_bulletin', 'student_download_bulletin_coupon']:
                return view_func(request, deliberation.id, *args, **kwargs)
            # Sinon, passer le token original
            return view_func(request, deliberation_token, *args, **kwargs)
        except Exception as e:
            # Log l'erreur pour débogage
            print(f"Erreur lors du décodage du token de délibération: {str(e)}")
            
            # Tenter de trouver une délibération pour l'utilisateur courant
            try:
                from .models import Student, StudentDeliberation, Deliberation
                if hasattr(request.user, 'student'):
                    student = request.user.student
                    # Trouver la délibération la plus récente de l'étudiant
                    student_delib = StudentDeliberation.objects.filter(
                        student=student
                    ).select_related('deliberation').order_by('-deliberation__date_scheduled').first()
                    
                    if student_delib:
                        # Rediriger vers la vue avec le bon token
                        if view_func.__name__ == 'student_download_bulletin':
                            return view_func(request, student_delib.deliberation.id)
                        elif view_func.__name__ == 'student_download_bulletin_coupon':
                            return view_func(request, student_delib.deliberation.id)
                
                # Si l'utilisateur est un membre du jury, rediriger vers la liste des délibérations
                if hasattr(request.user, 'jurymember'):
                    messages.error(request, "Token de délibération invalide: Aucune délibération correspondante trouvée")
                    return redirect('belletin:jury_deliberations_list')
            except Exception as inner_e:
                print(f"Erreur lors de la récupération de délibération de secours: {str(inner_e)}")
            
            # Message d'erreur générique
            messages.error(request, "Délibération introuvable. Veuillez contacter l'administration.")
            return redirect('belletin:dashboard')
    return wrapper

# Décorateur pour traiter les tokens d'étudiant
def with_decoded_student(view_func):
    """Décorateur qui décode le token d'étudiant avant d'exécuter la vue."""
    def wrapper(request, deliberation_token, student_token, *args, **kwargs):
        try:
            student_id = decode_id(student_token, expected_model='Student')
            # Ne pas ajouter student_id aux kwargs puisqu'on le passe déjà comme argument positionnel
            return view_func(request, deliberation_token, student_id, *args, **kwargs)
        except ValueError as e:
            messages.error(request, f"Token d'étudiant invalide: {str(e)}")
            return redirect('belletin:jury_deliberation_detail', deliberation_token=deliberation_token)
    return wrapper

@login_required
@with_decoded_deliberation
def jury_deliberation_detail(request, deliberation_token):
    """Version sécurisée de jury_deliberation_detail"""
    from .views import jury_deliberation_detail as original_view
    return original_view(request, deliberation_token)

@login_required
@with_decoded_deliberation
@with_decoded_student
def jury_student_detail(request, deliberation_token, student_id):
    """Version sécurisée de jury_student_detail"""
    from .views import jury_student_detail as original_view
    return original_view(request, deliberation_token, student_id)

@login_required
@with_decoded_deliberation
def jury_bulk_decision(request, deliberation_token):
    """Version sécurisée de jury_bulk_decision"""
    from .views import jury_bulk_decision as original_view
    return original_view(request, deliberation_token)

@login_required
@with_decoded_deliberation
def jury_complete_deliberation(request, deliberation_token):
    """Version sécurisée de jury_complete_deliberation"""
    from .views import jury_complete_deliberation as original_view
    return original_view(request, deliberation_token)

@login_required
@with_decoded_deliberation
def jury_export_pv(request, deliberation_token):
    """Version sécurisée de jury_export_pv"""
    from .views import jury_export_pv as original_view
    return original_view(request, deliberation_token)

@login_required
@with_decoded_deliberation
def jury_export_data(request, deliberation_token):
    """Version sécurisée de jury_export_data"""
    from .views import jury_export_data as original_view
    return original_view(request, deliberation_token)

@login_required
@with_decoded_deliberation
def student_download_bulletin(request, deliberation_token):
    """Version sécurisée de student_download_bulletin"""
    # La gestion des erreurs liées à WeasyPrint est maintenant incluse dans la vue originale
    # qui affichera silencieusement la version HTML en cas d'erreur de dépendances GTK/GObject
    from .views import student_download_bulletin as original_student_download_bulletin
    try:
        from .utils import resolve_deliberation_token
        deliberation = resolve_deliberation_token(deliberation_token)
        return original_student_download_bulletin(request, deliberation.id)
    except Exception as e:
        print(f"Erreur lors de la récupération du bulletin: {str(e)}")
        
        # En cas d'erreur, rechercher la délibération la plus récente pour cet étudiant
        try:
            from .models import Student, StudentDeliberation, Deliberation
            # Vérifier si l'utilisateur est un étudiant
            if hasattr(request.user, 'student'):
                student = request.user.student
                    # Trouver la délibération la plus récente pour l'étudiant
                student_delib = StudentDeliberation.objects.filter(
                        student=student
             ).select_related('deliberation').order_by('-deliberation__date_scheduled').first()
            
            if student_delib:
                    # Utiliser cette délibération
                return original_student_download_bulletin(request, student_delib.deliberation.id)
            else:
                # Si aucune délibération n'existe, chercher des délibérations pour la promotion
                delib = Deliberation.objects.filter(
                    promotion=student.promotion,
                    status='COMPLETED'
                ).order_by('-date_scheduled').first()
                    
            if delib:
                    # Créer un lien entre l'étudiant et la délibération
                    student_delib = StudentDeliberation(
                        deliberation=delib,
                        student=student,
                        average=0,
                        credits_obtained=0,
                        auto_decision='ADMITTED',
                        validated=True,
                        validated_at=timezone.now()
                    )
                    student_delib.save()
                    return original_student_download_bulletin(request, delib.id)
        except Exception as inner_e:
            print(f"Erreur lors de la récupération de délibération de secours: {str(inner_e)}")
        
        # Si tout échoue, afficher un message d'erreur
        messages.error(request, "Délibération introuvable. Veuillez contacter l'administration.")
        return redirect('belletin:student_bulletin')

@login_required
@with_decoded_deliberation
def student_download_bulletin_coupon(request, deliberation_token):
    """Version sécurisée de student_download_bulletin_coupon"""
    # La gestion des erreurs liées à WeasyPrint est maintenant incluse dans la vue originale
    # qui affichera silencieusement la version HTML en cas d'erreur de dépendances GTK/GObject
    from .views import student_download_bulletin_coupon as original_view
    try:
        from .utils import resolve_deliberation_token
        deliberation = resolve_deliberation_token(deliberation_token)
        
        # On s'assure que le token de délibération est valide
        if not deliberation:
            raise Exception("Délibération introuvable")
            
        # Appel à la vue originale avec l'ID de la délibération
        return original_view(request, deliberation.id)
    except Exception as e:
        print(f"Erreur lors de la récupération du coupon de bulletin: {str(e)}")
        
        # En cas d'erreur, rechercher la délibération la plus récente pour cet étudiant
        try:
            from .models import Student, StudentDeliberation, Deliberation
            # Vérifier si l'utilisateur est un étudiant
            if hasattr(request.user, 'student'):
                student = request.user.student
                    # Trouver la délibération la plus récente pour l'étudiant
                student_delib = StudentDeliberation.objects.filter(
                        student=student
                ).select_related('deliberation').order_by('-deliberation__date_scheduled').first()
                
            if student_delib:
                    # Utiliser cette délibération
                return original_view(request, student_delib.deliberation.id)
            else:
                    # Si aucune délibération n'existe, chercher des délibérations pour la promotion
                delib = Deliberation.objects.filter(
                    promotion=student.promotion,
                    status='COMPLETED'
                ).order_by('-date_scheduled').first()
                
                if delib:
                    # Créer un lien entre l'étudiant et la délibération
                    student_delib = StudentDeliberation(
                        deliberation=delib,
                        student=student,
                        average=0,
                        credits_obtained=0,
                        auto_decision='ADMITTED',
                        validated=True,
                        validated_at=timezone.now()
                    )
                    student_delib.save()
                    
                    # Utiliser cette délibération
                    return original_view(request, delib.id)
            
            # Si aucune délibération n'a été trouvée, on lève une exception spécifique
            raise Exception("Aucune délibération trouvée pour cet étudiant")
            
        except Exception as inner_e:
            print(f"Erreur lors de la récupération de délibération de secours: {str(inner_e)}")
        
        # Si tout échoue, afficher un message d'erreur
        messages.error(request, "Délibération introuvable. Veuillez contacter l'administration.")
        return redirect('belletin:student_bulletin') 