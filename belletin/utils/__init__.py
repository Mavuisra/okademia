# Fichier __init__.py pour transformer le dossier utils en package Python 
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
    Encode un ID en token sécurisé
    
    Args:
        id_value (int): L'ID à encoder
        model_name (str, optional): Nom du modèle associé
        
    Returns:
        str: Token encodé et sécurisé
    """
    # Vérifier que la valeur d'ID est valide
    if id_value is None or id_value <= 0:
        id_value = 1 if id_value is None else max(1, id_value)

    # Créer un dictionnaire avec les données à chiffrer
    data = {
        'id': id_value,
        'model': model_name
    }

    # Convertir le dictionnaire en chaîne JSON puis encoder en bytes
    data_json = json.dumps(data).encode()
    
    # Créer une signature HMAC pour vérifier l'intégrité
    signature = hmac.new(SECRET_KEY, data_json, hashlib.sha256).hexdigest()
    
    # Ajouter la signature au dictionnaire
    data['sig'] = signature
    
    # Convertir à nouveau en JSON
    secured_data = json.dumps(data).encode()
    
    # Chiffrer les données
    cipher = Fernet(get_encryption_key())
    encrypted_data = cipher.encrypt(secured_data)
    
    # Encoder en base64 URL-safe pour utilisation dans les URLs
    token = base64.urlsafe_b64encode(encrypted_data).decode()
    
    return token 

# Fonction pour décoder un token en ID
def decode_id(token, expected_model=None):
    """
    Décode un token sécurisé en ID
    
    Args:
        token (str): Token à décoder
        expected_model (str, optional): Nom du modèle attendu pour la vérification
        
    Returns:
        int: ID décodé
    
    Raises:
        ValueError: Si le token est invalide ou si le modèle ne correspond pas
    """
    try:
        # Décoder le token de base64 URL-safe
        encrypted_data = base64.urlsafe_b64decode(token)
        
        # Déchiffrer les données
        cipher = Fernet(get_encryption_key())
        decrypted_data = cipher.decrypt(encrypted_data)
        
        # Charger le JSON des données déchiffrées
        data = json.loads(decrypted_data.decode())
        
        # Extraire les données
        id_value = data['id']
        model_name = data.get('model')
        stored_signature = data.get('sig')
        
        # Recréer la signature pour vérification
        verification_data = {
            'id': id_value,
            'model': model_name
        }
        verification_json = json.dumps(verification_data).encode()
        verification_signature = hmac.new(SECRET_KEY, verification_json, hashlib.sha256).hexdigest()
        
        # Vérifier que les signatures correspondent
        if stored_signature != verification_signature:
            raise ValueError("Signature invalide")
        
        # Vérifier que le modèle correspond si spécifié
        if expected_model and model_name != expected_model:
            raise ValueError(f"Type de modèle incorrect: attendu {expected_model}, reçu {model_name}")
        
        return id_value
    except Exception as e:
        raise ValueError(f"Token invalide: {str(e)}")

# Fonction pour résoudre un token de délibération en instance de modèle
def resolve_deliberation_token(token):
    """
    Résout un token de délibération en instance du modèle Deliberation
    
    Args:
        token (str): Token de délibération
        
    Returns:
        Deliberation: Instance du modèle Deliberation
        
    Raises:
        ValueError: Si le token est invalide ou si la délibération n'existe pas
    """
    from belletin.models import Deliberation
    
    try:
        # Si le token est un objet Deliberation, le retourner directement
        if hasattr(token, 'id') and isinstance(token, Deliberation):
            return token
        
        # Vérifier si c'est un ID direct (entier)
        if isinstance(token, int) and token > 0:
            delib = Deliberation.objects.get(id=token)
            return delib
        
        # Sinon, essayer de décoder le token
        try:
            deliberation_id = decode_id(token, expected_model='Deliberation')
            delib = Deliberation.objects.get(id=deliberation_id)
            return delib
        except Exception as e:
            # Si échec, essayer de trouver la délibération par son token stocké
            delib = Deliberation.objects.filter(token=token).first()
            if delib:
                return delib
            raise ValueError(f"Impossible de résoudre le token: {str(e)}")
    except Exception as e:
        # Vérifier l'accès courant
        try:
            # Vérifier si l'utilisateur actuel a le droit d'accéder à cette délibération
            # On utilise une variable spéciale attachée à la fonction pour accéder à la requête actuelle
            current_user = getattr(getattr(resolve_deliberation_token, 'request', None), 'user', None)
            if current_user and not current_user.is_anonymous:
                # Vérifier les droits d'accès (à personnaliser selon votre modèle de sécurité)
                pass
        except Exception:
            pass
        
        raise ValueError(f"Token de délibération invalide ou délibération inexistante: {str(e)}")

def synchronize_all_grades():
    """
    Synchronise toutes les composantes de notes (GradeComponent) avec le modèle Grade.
    Cette fonction doit être appelée lorsque les notes n'ont pas été correctement enregistrées
    dans la table Grade.
    """
    from belletin.models import Course, Student, GradeComponent, Grade
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
            if 'CC' in component_dict and 'MC' in component_dict:
                # Récupérer directement CC et MC
                cc = component_dict['CC']
                mc = component_dict['MC']

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