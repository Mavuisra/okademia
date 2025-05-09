import json
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages

from belletin.models import Notification, PushSubscription, NotificationPreference
# Importation relative plus sûre
from .utils.push_notifications import get_vapid_keys

@login_required
def notifications_settings(request):
    """
    Affiche la page de gestion des notifications
    """
    # Récupérer les notifications de l'utilisateur
    notifications = Notification.objects.filter(user=request.user)
    
    # Récupérer les préférences de notification
    preferences = {pref.notification_type: pref.enabled 
                    for pref in NotificationPreference.objects.filter(user=request.user)}
    
    # Compter les notifications non lues
    unread_count = notifications.filter(read=False).count()
    
    context = {
        'notifications': notifications,
        'preferences': preferences,
        'unread_notifications_count': unread_count
    }
    
    return render(request, 'belletin/notifications/settings.html', context)

@login_required
@require_GET
def vapid_public_key(request):
    """
    Renvoie la clé publique VAPID pour l'application web
    """
    vapid_keys = get_vapid_keys()
    return JsonResponse({'publicKey': vapid_keys['public_key']})

@login_required
@require_POST
def subscription(request):
    """
    Gère les abonnements aux notifications push
    """
    data = json.loads(request.body)
    subscription_data = data.get('subscription', {})
    user_agent = data.get('userAgent', '')
    
    if not subscription_data:
        return JsonResponse({'error': 'Données d\'abonnement manquantes'}, status=400)
    
    # Extraction des données d'abonnement
    endpoint = subscription_data.get('endpoint')
    p256dh = subscription_data.get('keys', {}).get('p256dh')
    auth = subscription_data.get('keys', {}).get('auth')
    
    if not all([endpoint, p256dh, auth]):
        return JsonResponse({'error': 'Données d\'abonnement incomplètes'}, status=400)
    
    # Enregistrer l'abonnement
    try:
        subscription, created = PushSubscription.objects.update_or_create(
            user=request.user,
            endpoint=endpoint,
            defaults={
                'p256dh': p256dh,
                'auth': auth,
                'user_agent': user_agent
            }
        )
        
        # Création des préférences par défaut si premier abonnement
        if created:
            for notification_type, _ in NotificationPreference.NOTIFICATION_TYPES:
                NotificationPreference.objects.get_or_create(
                    user=request.user,
                    notification_type=notification_type,
                    defaults={'enabled': True}
                )
        
        return JsonResponse({'success': True, 'created': created})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def delete_subscription(request):
    """
    Supprime un abonnement aux notifications push
    """
    data = json.loads(request.body)
    subscription_data = data.get('subscription', {})
    
    if not subscription_data:
        return JsonResponse({'error': 'Données d\'abonnement manquantes'}, status=400)
    
    endpoint = subscription_data.get('endpoint')
    
    if not endpoint:
        return JsonResponse({'error': 'Endpoint manquant'}, status=400)
    
    try:
        subscription = PushSubscription.objects.filter(
            user=request.user,
            endpoint=endpoint
        ).delete()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def update_subscription_status(request):
    """
    Met à jour le statut d'abonnement
    """
    data = json.loads(request.body)
    is_subscribed = data.get('isSubscribed', False)
    status = data.get('status', '')
    
    # On pourrait enregistrer ce statut dans le profil utilisateur
    # pour des statistiques ou des fonctionnalités supplémentaires
    
    return JsonResponse({'success': True})

@login_required
@require_POST
def update_preferences(request):
    """
    Met à jour les préférences de notification
    """
    data = json.loads(request.body)
    notification_type = data.get('type')
    enabled = data.get('enabled', True)
    
    if not notification_type:
        return JsonResponse({'error': 'Type de notification manquant'}, status=400)
    
    try:
        preference, created = NotificationPreference.objects.update_or_create(
            user=request.user,
            notification_type=notification_type,
            defaults={'enabled': enabled}
        )
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """
    Marque une notification comme lue
    """
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.mark_as_read()
    
    return JsonResponse({'success': True})

@login_required
def delete_notification(request, notification_id):
    """
    Supprime une notification
    """
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.delete()
    
    messages.success(request, "Notification supprimée avec succès")
    return redirect('belletin:notifications')

@login_required
def mark_all_read(request):
    """
    Marque toutes les notifications comme lues
    """
    Notification.objects.filter(user=request.user, read=False).update(read=True)
    
    messages.success(request, "Toutes les notifications ont été marquées comme lues")
    return redirect('belletin:notifications')

@login_required
def clear_all_notifications(request):
    """
    Supprime toutes les notifications
    """
    Notification.objects.filter(user=request.user).delete()
    
    messages.success(request, "Toutes les notifications ont été supprimées")
    return redirect('belletin:notifications')

# Exemple d'API pour tester l'envoi de notification
@login_required
def send_test_notification(request):
    """
    Envoie une notification de test
    """
    # Importation locale pour éviter les erreurs circulaires
    from .utils.push_notifications import create_notification
    
    create_notification(
        user=request.user,
        title="Notification de test",
        message="Ceci est une notification de test pour vérifier que les notifications push fonctionnent correctement.",
        notification_type="announcements",
        url=request.build_absolute_uri('/'),
        send_now=True
    )
    
    messages.success(request, "Notification de test envoyée avec succès")
    return redirect('belletin:notifications') 