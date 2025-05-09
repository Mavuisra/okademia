import json
import base64
import os
from django.conf import settings
from pywebpush import webpush, WebPushException

def get_vapid_keys():
    """
    Récupère les clés VAPID depuis les paramètres ou génère de nouvelles clés si nécessaires
    """
    if hasattr(settings, 'VAPID_PRIVATE_KEY') and hasattr(settings, 'VAPID_PUBLIC_KEY'):
        return {
            'private_key': settings.VAPID_PRIVATE_KEY,
            'public_key': settings.VAPID_PUBLIC_KEY
        }
    else:
        # Si les clés ne sont pas dans les paramètres, on peut générer des clés temporaires
        # Attention: ces clés seront perdues au redémarrage du serveur
        # Il est recommandé de générer des clés avec pywebpush et de les stocker dans settings.py
        from pywebpush import WebPusher
        vapid_keys = WebPusher.generate_vapid_keys()
        return {
            'private_key': vapid_keys['private_key'],
            'public_key': vapid_keys['public_key']
        }

def send_push_notification(subscription_info, payload):
    """
    Envoie une notification push à un abonnement
    
    Args:
        subscription_info (dict): Informations d'abonnement (endpoint, keys)
        payload (dict): Contenu de la notification (title, body, etc.)
    
    Returns:
        bool: Succès de l'envoi
    """
    vapid_keys = get_vapid_keys()
    
    try:
        response = webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=vapid_keys['private_key'],
            vapid_claims={
                'sub': f"mailto:{settings.WEBPUSH_CONTACT_EMAIL if hasattr(settings, 'WEBPUSH_CONTACT_EMAIL') else 'admin@example.com'}"
            }
        )
        return True
    except WebPushException as e:
        # Logging de l'erreur
        print(f"Erreur WebPush: {e}")
        # Retour de l'exception pour traitement par l'appelant
        raise e
    except Exception as e:
        print(f"Erreur lors de l'envoi de la notification push: {e}")
        raise e

def create_notification(user, title, message, notification_type, url=None, icon=None, send_now=True):
    """
    Crée une notification et l'envoie si demandé
    
    Args:
        user (User): Utilisateur destinataire
        title (str): Titre de la notification
        message (str): Corps de la notification
        notification_type (str): Type de notification (grades, deliberations, etc.)
        url (str, optional): URL associée à la notification
        icon (str, optional): Icône à afficher
        send_now (bool, optional): Envoyer immédiatement la notification
    
    Returns:
        Notification: L'objet notification créé
    """
    from belletin.models import Notification
    
    # Création de la notification
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        url=url,
        icon=icon
    )
    
    # Envoi immédiat si demandé
    if send_now:
        notification.send_push()
    
    return notification

def send_bulk_notification(users, title, message, notification_type, url=None, icon=None):
    """
    Envoie une notification à plusieurs utilisateurs
    
    Args:
        users (QuerySet): Queryset d'utilisateurs
        title (str): Titre de la notification
        message (str): Corps de la notification
        notification_type (str): Type de notification
        url (str, optional): URL associée
        icon (str, optional): Icône à afficher
    
    Returns:
        list: Liste des notifications créées
    """
    notifications = []
    
    for user in users:
        notification = create_notification(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            url=url,
            icon=icon,
            send_now=True
        )
        notifications.append(notification)
    
    return notifications 