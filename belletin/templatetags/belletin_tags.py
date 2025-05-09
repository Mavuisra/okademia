from django import template
from django.urls import reverse
from ..utils import encode_id

register = template.Library()

@register.simple_tag
def secure_url(view_name, **kwargs):
    """
    Tag de template pour générer des URLs sécurisées avec des tokens
    au lieu d'IDs numériques.
    
    Usage:
        {% secure_url 'jury_student_detail' deliberation_id=delib.id student_id=student.id %}
        ou
        {% secure_url 'jury_student_detail' deliberation_token=delib.token student_token=student.token %}
    """
    # Liste des paramètres à encoder pour chaque vue
    secure_params = {
        'jury_student_detail': [('deliberation_id', 'Deliberation', 'deliberation_token'), 
                              ('student_id', 'Student', 'student_token')],
        'jury_deliberation_detail': [('deliberation_id', 'Deliberation', 'deliberation_token')],
        'jury_bulk_decision': [('deliberation_id', 'Deliberation', 'deliberation_token')],
        'jury_complete_deliberation': [('deliberation_id', 'Deliberation', 'deliberation_token')],
        'jury_export_pv': [('deliberation_id', 'Deliberation', 'deliberation_token')],
        'jury_export_data': [('deliberation_id', 'Deliberation', 'deliberation_token')],
        'student_download_bulletin': [('deliberation_id', 'Deliberation', 'deliberation_token')],
        'student_download_bulletin_coupon': [('deliberation_id', 'Deliberation', 'deliberation_token')],
    }
    
    # Vérifier si la vue nécessite des tokens sécurisés
    if view_name in secure_params:
        # Nouvelles valeurs de paramètres pour l'URL
        new_kwargs = {}
        
        for param_id, model_name, param_token in secure_params[view_name]:
            # Vérifier si le token est déjà fourni
            if param_token in kwargs:
                # Utiliser le token directement
                new_kwargs[param_token] = kwargs[param_token]
            elif param_id in kwargs:
                # Encoder l'ID en token
                token = encode_id(kwargs[param_id], model_name)
                # Utiliser le nom du paramètre de token dans l'URL
                new_kwargs[param_token] = token
            else:
                # Si aucun paramètre n'est fourni, chercher dans les autres
                found = False
                for key, value in kwargs.items():
                    if key == param_token:
                        new_kwargs[param_token] = value
                        found = True
                        break
                
                if not found:
                    # Si aucun paramètre correspondant n'est trouvé, c'est une erreur
                    raise ValueError(f"Paramètre manquant pour {view_name}: {param_id} ou {param_token}")
        
        # Générer l'URL avec les tokens
        return reverse(f'belletin:{view_name}', kwargs=new_kwargs)
    else:
        # Pour les vues qui n'utilisent pas de tokens, simplement passer les paramètres tels quels
        return reverse(f'belletin:{view_name}', kwargs=kwargs)

@register.filter
def tokenize(value, model_name=None):
    """
    Filtre de template pour convertir un ID en token.
    
    Usage:
        {{ student.id|tokenize:"Student" }}
    """
    return encode_id(value, model_name) 