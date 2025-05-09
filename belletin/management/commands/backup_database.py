import os
import datetime
import shutil
import subprocess
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection

class Command(BaseCommand):
    help = 'Sauvegarde la base de données'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep',
            type=int,
            default=10,
            help='Nombre de sauvegardes à conserver'
        )

    def handle(self, *args, **options):
        # Créer le dossier de sauvegarde s'il n'existe pas
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Nom de fichier avec date et heure
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Détecter le type de base de données
        db_engine = connection.settings_dict['ENGINE']
        
        if 'sqlite3' in db_engine:
            # Pour SQLite, faire une simple copie du fichier
            db_path = connection.settings_dict['NAME']
            backup_file = os.path.join(backup_dir, f'backup_{timestamp}.sqlite3')
            
            self.stdout.write(f'Sauvegarde de la base de données SQLite vers {backup_file}')
            shutil.copy2(db_path, backup_file)
        
        elif 'postgresql' in db_engine:
            # Pour PostgreSQL, utiliser pg_dump
            db_name = connection.settings_dict['NAME']
            db_user = connection.settings_dict['USER']
            db_host = connection.settings_dict.get('HOST', 'localhost')
            db_password = connection.settings_dict['PASSWORD']
            
            backup_file = os.path.join(backup_dir, f'backup_{timestamp}.sql')
            
            # Créer un fichier temporaire pour le mot de passe
            pgpass_file = os.path.join(backup_dir, '.pgpass_temp')
            with open(pgpass_file, 'w') as f:
                f.write(f'{db_host}:5432:{db_name}:{db_user}:{db_password}')
            os.chmod(pgpass_file, 0o600)
            
            # Définir la variable d'environnement pour pg_dump
            env = os.environ.copy()
            env['PGPASSFILE'] = pgpass_file
            
            self.stdout.write(f'Sauvegarde de la base de données PostgreSQL vers {backup_file}')
            
            try:
                subprocess.run(
                    [
                        'pg_dump',
                        '-h', db_host,
                        '-U', db_user,
                        '-d', db_name,
                        '-f', backup_file
                    ],
                    env=env,
                    check=True
                )
            except subprocess.CalledProcessError as e:
                self.stdout.write(self.style.ERROR(f'Erreur lors de la sauvegarde: {e}'))
            finally:
                # Supprimer le fichier de mot de passe temporaire
                if os.path.exists(pgpass_file):
                    os.unlink(pgpass_file)
        
        else:
            self.stdout.write(self.style.ERROR(f'Type de base de données non pris en charge: {db_engine}'))
            return
        
        self.stdout.write(self.style.SUCCESS('Sauvegarde terminée avec succès!'))
        
        # Nettoyer les anciennes sauvegardes
        self._cleanup_old_backups(backup_dir, options['keep'])
    
    def _cleanup_old_backups(self, backup_dir, keep):
        """Supprime les sauvegardes les plus anciennes en ne gardant que 'keep' sauvegardes."""
        backups = []
        
        for filename in os.listdir(backup_dir):
            if filename.startswith('backup_') and (filename.endswith('.sqlite3') or filename.endswith('.sql')):
                filepath = os.path.join(backup_dir, filename)
                file_time = os.path.getmtime(filepath)
                backups.append((filepath, file_time))
        
        # Trier par date (la plus récente en premier)
        backups.sort(key=lambda x: x[1], reverse=True)
        
        # Supprimer les sauvegardes anciennes
        if len(backups) > keep:
            for filepath, _ in backups[keep:]:
                os.unlink(filepath)
                self.stdout.write(f'Ancienne sauvegarde supprimée: {filepath}') 