from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from .offline import OfflineSynchronizer
from django.template.response import TemplateResponse
from .models import OfflineQueue

@login_required
@csrf_protect
@require_POST
def synchronize_offline_data(request):
    """
    Endpoint API pour synchroniser les données hors ligne.
    Cette vue est appelée automatiquement lorsque la connexion est rétablie.
    """
    success_count, failure_count, remaining = OfflineSynchronizer.process_queue()
    
    return JsonResponse({
        'success': True,
        'processed': success_count,
        'failed': failure_count,
        'remaining': remaining,
        'message': f"{success_count} opérations synchronisées avec succès. {failure_count} échecs. {remaining} en attente."
    })

@login_required
def offline_queue_status(request):
    """
    Affiche l'état de la file d'attente hors ligne pour l'utilisateur.
    """
    # Récupérer les éléments en attente pour l'utilisateur actuel
    pending_items = OfflineQueue.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    # Statistiques
    pending_count = pending_items.filter(status='PENDING').count()
    processing_count = pending_items.filter(status='PROCESSING').count()
    completed_count = pending_items.filter(status='COMPLETED').count()
    failed_count = pending_items.filter(status='FAILED').count()
    
    context = {
        'pending_items': pending_items,
        'stats': {
            'pending': pending_count,
            'processing': processing_count,
            'completed': completed_count,
            'failed': failed_count,
            'total': pending_items.count()
        }
    }
    
    return TemplateResponse(request, 'offline/queue_status.html', context)
