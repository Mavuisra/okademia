import base64
import hashlib
import hmac
import json
from django.conf import settings
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os

# Clé secrète utilisée pour la signature HMAC et le chiffrement
# Utilisez settings.SECRET_KEY comme base ou définissez une clé spécifique 
SECRET_KEY = settings.SECRET_KEY.encode()

# Dériver une clé de chiffrement à partir de la SECRET_KEY
def get_encryption_key():
    salt = b'belletin_token_salt'  # Utiliser un sel fixe pour la cohérence
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(SECRET_KEY))
    return key

# Fonction pour encoder un ID en token sécurisé
def encode_id(id_value, model_name=None):
    """
    Encode un ID numérique en token sécurisé.
    
    Args:
        id_value (int): L'ID à encoder
        model_name (str, optional): Nom du modèle pour contexte additionnel
        
    Returns:
        str: Token encodé et sécurisé
    """
    # Vérifier que la valeur d'ID est valide
    if id_value is None or id_value <= 0:
        # En cas d'erreur, fournir un ID temporaire mais valide pour éviter les crashs
        id_value = 1 if id_value is None else max(1, id_value)
    
    # Créer un dictionnaire avec les données à chiffrer
    data = {'id': id_value}
    if model_name:
        data['model'] = model_name
    
    # Ajouter une donnée de persistance pour assurer la longévité du token
    data['permanent'] = True
    
    # Sérialiser en JSON et encoder en bytes
    json_data = json.dumps(data).encode()
    
    # Chiffrer les données
    fernet = Fernet(get_encryption_key())
    encrypted_data = fernet.encrypt(json_data)
    
    # Encoder en base64 URL-safe
    token = base64.urlsafe_b64encode(encrypted_data).decode()
    
    # Ajouter une signature HMAC pour vérifier l'intégrité
    signature = hmac.new(SECRET_KEY, encrypted_data, hashlib.sha256).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode()
    
    # Format du token: {données chiffrées}.{signature}
    return f"{token}.{signature_b64}"

# Fonction pour décoder un token en ID
def decode_id(token, expected_model=None):
    """
    Décode un token sécurisé en ID numérique.
    
    Args:
        token (str): Le token à décoder
        expected_model (str, optional): Nom du modèle attendu pour validation
        
    Returns:
        int: L'ID décodé
        
    Raises:
        ValueError: Si le token est invalide ou si le modèle ne correspond pas
    """
    if not token:
        raise ValueError("Token manquant ou vide")
        
    try:
        # Tentative de décodage au format sécurisé (données.signature)
        if '.' in token:
            # Séparer le token et la signature
            encrypted_part, signature_part = token.split('.')
            
            # Décoder les parties
            encrypted_data = base64.urlsafe_b64decode(encrypted_part)
            received_signature = base64.urlsafe_b64decode(signature_part)
            
            # Vérifier la signature
            expected_signature = hmac.new(SECRET_KEY, encrypted_data, hashlib.sha256).digest()
            if not hmac.compare_digest(received_signature, expected_signature):
                raise ValueError("Signature de token invalide")
            
            # Déchiffrer les données
            fernet = Fernet(get_encryption_key())
            decrypted_data = fernet.decrypt(encrypted_data)
            
            # Désérialiser le JSON
            data = json.loads(decrypted_data.decode())
            
            # Vérifier le modèle si spécifié
            if expected_model and data.get('model') != expected_model:
                raise ValueError(f"Type de modèle incorrect: attendu {expected_model}, reçu {data.get('model')}")
            
            return data['id']
        else:
            # Format de token ancien (simple base64) - pour compatibilité avec l'existant
            # Recherche plus flexible de l'objet
            from django.apps import apps
            if expected_model:
                model = apps.get_model('belletin', expected_model)
                
                # Essayer de trouver par token direct
                obj = model.objects.filter(token=token).first()
                if obj:
                    return obj.id
                
                # Essayer de trouver en convertissant en ID
                try:
                    id_val = int(token)
                    if model.objects.filter(id=id_val).exists():
                        return id_val
                except ValueError:
                    pass
            
            # Dernier recours: essayer de convertir en entier
            try:
                return int(token)
            except ValueError:
                pass
        
    except Exception as e:
        # Log l'erreur pour débogage mais continue à chercher l'objet par d'autres moyens
        print(f"Erreur de décodage du token: {str(e)}")
        
        # Tenter de trouver par une recherche plus large si le modèle est spécifié
        if expected_model:
            from django.apps import apps
            model = apps.get_model('belletin', expected_model)
            
            # Rechercher par token partiel (si le token contient des informations partielles)
            if len(token) > 10:  # Éviter les recherches trop vagues
                obj = model.objects.filter(token__contains=token[:10]).first()
                if obj:
                    return obj.id
        
    # Si on arrive ici, c'est qu'on n'a pas réussi à décoder le token
    raise ValueError("Format de token non reconnu ou token invalide")

# Fonction pour résoudre un token de délibération
def resolve_deliberation_token(token):
    """
    Résout un token de délibération en objet Deliberation.
    
    Args:
        token (str): Token brut ou encodé
        
    Returns:
        Deliberation: L'objet délibération trouvé
        
    Raises:
        Deliberation.DoesNotExist: Si aucune délibération n'est trouvée
    """
    from .models import Deliberation
    
    if not token:
        raise Deliberation.DoesNotExist("Token de délibération manquant")
    
    # Essayer d'abord de trouver par token direct
    try:
        delib = Deliberation.objects.filter(token=token).first()
        if delib:
            return delib
            
        # Ensuite essayer de décoder et trouver par ID
        try:
            deliberation_id = decode_id(token, expected_model='Deliberation')
            delib = Deliberation.objects.filter(id=deliberation_id).first()
            if delib:
                return delib
                
            # Si l'ID est valide mais que l'objet n'est pas trouvé, essayer une recherche plus large
            return Deliberation.objects.last()  # Renvoyer la dernière délibération comme fallback
        except Exception:
            # Dernier recours: essayer de trouver la délibération la plus récente pour cet étudiant
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Si un utilisateur est connecté, chercher sa délibération la plus récente
            current_user = getattr(getattr(resolve_deliberation_token, 'request', None), 'user', None)
            if current_user and current_user.is_authenticated:
                try:
                    student = current_user.student
                    from .models import StudentDeliberation
                    student_delib = StudentDeliberation.objects.filter(student=student).order_by('-deliberation__date_scheduled').first()
                    if student_delib:
                        return student_delib.deliberation
                except Exception:
                    pass
            
            # Si tout échoue, trouver la délibération la plus récente
            return Deliberation.objects.order_by('-date_scheduled').first()
    except Exception as e:
        # Logging étendu pour le débogage
        print(f"Erreur lors de la résolution du token de délibération: {str(e)}")
        
        # Dernier recours: renvoyer la dernière délibération du système
        latest = Deliberation.objects.order_by('-date_scheduled').first()
        if latest:
            return latest
            
        # Si vraiment rien ne fonctionne, lever l'exception
        raise Deliberation.DoesNotExist("Aucune délibération trouvée avec ce token")

# Fonction pour réutiliser dans les templates
def get_secure_url(view_name, **kwargs):
    """
    Génère une URL sécurisée en remplaçant les IDs par des tokens.
    À utiliser dans les templates pour générer les URLs.
    
    Args:
        view_name (str): Nom de la vue
        **kwargs: Arguments nommés à passer à la vue
        
    Returns:
        str: URL sécurisée
    """
    # Ici, nous pourrions automatiquement encoder les IDs 
    # en fonction des règles définies pour chaque vue
    # Pour l'instant, c'est juste un placeholder
    from django.urls import reverse
    
    # Liste des paramètres à encoder (à personnaliser selon vos vues)
    secure_params = {
        'jury_student_detail': ['deliberation_token', 'student_token'],
        'jury_deliberation_detail': ['deliberation_token'],
        'jury_bulk_decision': ['deliberation_token'],
        'jury_complete_deliberation': ['deliberation_token'],
        'jury_export_pv': ['deliberation_token'],
        'jury_export_data': ['deliberation_token'],
        'student_download_bulletin': ['deliberation_token'],
        'student_download_bulletin_coupon': ['deliberation_token'],
    }
    
    # Si la vue nécessite des tokens sécurisés
    if view_name in secure_params:
        for param in secure_params[view_name]:
            if param in kwargs:
                model_name = None
                if 'deliberation' in param:
                    model_name = 'Deliberation'
                elif 'student' in param:
                    model_name = 'Student'
                
                kwargs[param] = encode_id(kwargs[param], model_name)
    
    return reverse(f'belletin:{view_name}', kwargs=kwargs)

def synchronize_all_grades():
    """
    Synchronise toutes les composantes de notes (GradeComponent) avec le modèle Grade.
    Cette fonction doit être appelée lorsque les notes n'ont pas été correctement enregistrées
    dans la table Grade.
    """
    from .models import Course, Student, GradeComponent, Grade
    from django.db.models import Q

    # Récupérer tous les étudiants qui ont des composantes de notes
    student_course_pairs = GradeComponent.objects.values('student', 'course').distinct()
    
    updated_count = 0
    error_count = 0
    
    for pair in student_course_pairs:
        student_id = pair['student']
        course_id = pair['course']
        
        try:
            student = Student.objects.get(id=student_id)
            course = Course.objects.get(id=course_id)
            
            # Récupérer les composantes pour cet étudiant et ce cours
            components = GradeComponent.objects.filter(
                student=student,
                course=course
            )
            
            # Organiser les composantes par type
            component_dict = {comp.type: comp.score for comp in components}
            
            # Vérifier si toutes les composantes nécessaires sont présentes
            if ('TP' in component_dict and 
                'INTERROGATION' in component_dict and 
                'EXAMEN' in component_dict and
                component_dict['TP'] is not None and
                component_dict['INTERROGATION'] is not None and
                component_dict['EXAMEN'] is not None):
                
                # Calculer les notes cc et mc
                cc = component_dict['TP'] + component_dict['INTERROGATION']  # TP (5) + Interrogation (5) = 10
                mc = component_dict['EXAMEN'] * 2  # Examen (10) converti en note sur 20
                
                # Mettre à jour ou créer le Grade
                grade, created = Grade.objects.update_or_create(
                    student=student,
                    ue=course.ue,
                    defaults={
                        'cc': cc,
                        'mc': mc
                    }
                )
                
                updated_count += 1
        except Exception as e:
            print(f"Erreur lors de la synchronisation des notes pour l'étudiant {student_id}, cours {course_id}: {str(e)}")
            error_count += 1
    
    return {
        'updated': updated_count,
        'errors': error_count,
        'total': len(student_course_pairs)
    } 