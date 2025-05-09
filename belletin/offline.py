import json
from django.db import transaction
from django.core.serializers.json import DjangoJSONEncoder
from .models import OfflineQueue

class OfflineMixin:
    """
    Mixin pour gérer les opérations en mode hors ligne.
    À utiliser dans les vues pour détecter si l'utilisateur est hors ligne
    et enregistrer les opérations pour une synchronisation ultérieure.
    """
    
    def is_offline_request(self, request):
        """Détermine si la requête est en mode hors ligne"""
        return request.POST.get('offline_mode') == 'true' or request.headers.get('X-Offline-Mode') == 'true'
    
    def queue_offline_operation(self, request, operation_type, model_name, object_id, data):
        """
        Enregistre une opération pour une synchronisation ultérieure.
        
        Args:
            request: La requête HTTP
            operation_type: Type d'opération ('CREATE', 'UPDATE', 'DELETE')
            model_name: Nom du modèle concerné
            object_id: ID de l'objet concerné (ou None pour CREATE)
            data: Données de l'opération (dictionnaire)
        
        Returns:
            OfflineQueue: L'objet créé dans la file d'attente
        """
        queue_item = OfflineQueue.objects.create(
            operation_type=operation_type,
            model_name=model_name,
            object_id=str(object_id) if object_id else '',
            user=request.user,
            data=data
        )
        return queue_item


class OfflineSynchronizer:
    """
    Classe pour synchroniser les opérations en attente
    lorsque la connexion est rétablie.
    """
    
    @classmethod
    def process_queue(cls, limit=50):
        """
        Traite les éléments en attente dans la file d'attente.
        
        Args:
            limit: Nombre maximum d'éléments à traiter
        
        Returns:
            tuple: (succès, échecs, non_traités)
        """
        pending_items = OfflineQueue.objects.filter(
            status='PENDING'
        ).order_by('created_at')[:limit]
        
        success_count = 0
        failure_count = 0
        
        for item in pending_items:
            try:
                with transaction.atomic():
                    item.status = 'PROCESSING'
                    item.save()
                    
                    # Appeler la méthode spécifique au type d'opération
                    if item.operation_type == 'CREATE':
                        cls._process_create(item)
                    elif item.operation_type == 'UPDATE':
                        cls._process_update(item)
                    elif item.operation_type == 'DELETE':
                        cls._process_delete(item)
                    
                    item.status = 'COMPLETED'
                    item.save()
                    success_count += 1
            
            except Exception as e:
                item.status = 'FAILED'
                item.error_message = str(e)
                item.retry_count += 1
                item.save()
                failure_count += 1
        
        remaining = OfflineQueue.objects.filter(status='PENDING').count()
        return success_count, failure_count, remaining
    
    @classmethod
    def _process_create(cls, queue_item):
        """Traite une opération de création"""
        from django.apps import apps
        
        model = apps.get_model(app_label='belletin', model_name=queue_item.model_name)
        data = queue_item.data
        
        # Supprimer les champs qui ne sont pas des champs du modèle
        for key in list(data.keys()):
            if key not in [field.name for field in model._meta.fields]:
                del data[key]
        
        # Créer l'objet
        instance = model.objects.create(**data)
        
        # Mettre à jour l'ID pour référence future
        queue_item.object_id = str(instance.id)
        queue_item.save(update_fields=['object_id'])
    
    @classmethod
    def _process_update(cls, queue_item):
        """Traite une opération de mise à jour"""
        from django.apps import apps
        
        model = apps.get_model(app_label='belletin', model_name=queue_item.model_name)
        data = queue_item.data
        
        # Récupérer l'instance à mettre à jour
        instance = model.objects.get(id=queue_item.object_id)
        
        # Mettre à jour les champs
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        
        instance.save()
    
    @classmethod
    def _process_delete(cls, queue_item):
        """Traite une opération de suppression"""
        from django.apps import apps
        
        model = apps.get_model(app_label='belletin', model_name=queue_item.model_name)
        
        # Récupérer l'instance à supprimer
        instance = model.objects.get(id=queue_item.object_id)
        
        # Supprimer l'instance
        instance.delete()


# Détection de la connectivité réseau côté JavaScript (à inclure dans un template ou fichier JS)
OFFLINE_JS = """
// Détection de la connectivité réseau
document.addEventListener('DOMContentLoaded', function() {
    // Initialiser l'état de la connexion
    updateOnlineStatus();
    
    // Écouter les changements d'état de la connexion
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    
    // Intercepter les soumissions de formulaires en mode hors ligne
    document.addEventListener('submit', handleFormSubmit);
});

// Mettre à jour l'état de la connexion
function updateOnlineStatus() {
    const isOnline = navigator.onLine;
    document.body.classList.toggle('offline-mode', !isOnline);
    
    // Afficher une notification
    if (!isOnline) {
        showNotification('Mode hors ligne activé', 'Les modifications seront synchronisées lorsque la connexion sera rétablie.');
    } else {
        showNotification('Connexion rétablie', 'Synchronisation des données en cours...');
        synchronizeOfflineData();
    }
}

// Gérer la soumission de formulaire
function handleFormSubmit(event) {
    if (!navigator.onLine) {
        const form = event.target;
        
        // Vérifier si le formulaire peut être mis en file d'attente
        if (form.hasAttribute('data-offline-support')) {
            event.preventDefault();
            
            // Ajouter un champ caché pour indiquer le mode hors ligne
            const offlineInput = document.createElement('input');
            offlineInput.type = 'hidden';
            offlineInput.name = 'offline_mode';
            offlineInput.value = 'true';
            form.appendChild(offlineInput);
            
            // Continuer la soumission du formulaire
            form.submit();
        }
    }
}

// Synchroniser les données hors ligne
function synchronizeOfflineData() {
    if (navigator.onLine) {
        fetch('/api/synchronize-offline-data/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Synchronisation terminée', `${data.processed} opérations synchronisées avec succès.`);
            } else {
                showNotification('Erreur de synchronisation', data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Erreur de synchronisation:', error);
        });
    }
}

// Afficher une notification
function showNotification(title, message, type = 'info') {
    // Implémenter votre propre logique de notification ici
    console.log(`[${type.toUpperCase()}] ${title}: ${message}`);
    
    // Exemple avec une notification simple
    if (typeof toast !== 'undefined') {
        toast(message, { type: type });
    } else {
        const notificationDiv = document.createElement('div');
        notificationDiv.className = `notification notification-${type}`;
        notificationDiv.innerHTML = `<strong>${title}</strong>: ${message}`;
        
        document.body.appendChild(notificationDiv);
        
        setTimeout(() => {
            notificationDiv.remove();
        }, 5000);
    }
}

// Obtenir le token CSRF
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}
""" 