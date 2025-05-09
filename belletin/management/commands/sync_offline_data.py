from django.core.management.base import BaseCommand
from django.utils import timezone
from belletin.offline import OfflineSynchronizer
import logging

logger = logging.getLogger('django')

class Command(BaseCommand):
    help = 'Synchronise les données en attente dans la file d\'attente hors ligne'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Nombre maximum d\'éléments à traiter en une seule exécution'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        
        self.stdout.write(f"Démarrage de la synchronisation des données hors ligne (limite: {limit})...")
        start_time = timezone.now()
        
        success_count, failure_count, remaining = OfflineSynchronizer.process_queue(limit=limit)
        
        duration = (timezone.now() - start_time).total_seconds()
        
        self.stdout.write(self.style.SUCCESS(
            f"Synchronisation terminée en {duration:.2f} secondes.\n"
            f"- {success_count} opérations réussies\n"
            f"- {failure_count} opérations échouées\n"
            f"- {remaining} opérations restantes"
        ))
        
        if failure_count > 0:
            self.stdout.write(self.style.WARNING(
                f"ATTENTION: {failure_count} opérations ont échoué. "
                f"Consultez l'interface d'administration pour plus de détails."
            ))
        
        return success_count, failure_count, remaining 