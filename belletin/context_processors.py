from .models import Notification

def notifications_processor(request):
    """
    Context processor pour ajouter le nombre de notifications non lues à toutes les pages
    """
    unread_notifications_count = 0
    
    if request.user.is_authenticated:
        unread_notifications_count = Notification.objects.filter(
            user=request.user, 
            read=False
        ).count()
    
    return {
        'unread_notifications_count': unread_notifications_count
    } 