from .utils import synchronize_all_grades
import time

class GradeSynchronizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Variable pour stocker le dernier temps de synchronisation
        self.last_sync_time = 0
        # Intervalle minimum entre les synchronisations (en secondes)
        self.sync_interval = 300  # 5 minutes

    def __call__(self, request):
        # Exécuter la synchronisation seulement si assez de temps s'est écoulé
        # depuis la dernière synchronisation (évite de surcharger la BD)
        current_time = time.time()
        if current_time - self.last_sync_time > self.sync_interval:
            # Exécuter la synchronisation seulement pour les pages professeur
            if request.path.startswith('/professor/') and request.user.is_authenticated:
                try:
                    # Vérifier si l'utilisateur est un professeur
                    hasattr(request.user, 'professor')
                    
                    # Synchroniser les notes en arrière-plan
                    # Note: dans un environnement de production, vous pourriez
                    # vouloir exécuter ceci de manière asynchrone
                    result = synchronize_all_grades()
                    print(f"Synchronisation automatique: {result['updated']} notes mises à jour")
                except Exception as e:
                    print(f"Erreur lors de la synchronisation automatique: {str(e)}")
                
                # Mettre à jour l'horodatage de la dernière synchronisation
                self.last_sync_time = current_time

        # Traiter la requête normalement
        response = self.get_response(request)
        return response 