#!/usr/bin/env python
"""
Script pour effectuer une sauvegarde automatique de la base de données.
À configurer avec cron (Linux) ou Task Scheduler (Windows).

Exemples:
- Linux: 0 2 * * * /chemin/vers/venv/bin/python /chemin/vers/cron_backup.py
- Windows: créer une tâche planifiée qui exécute python C:\chemin\vers\cron_backup.py

La sauvegarde sera effectuée et stockée dans le dossier 'backups'.
"""

import os
import sys
import subprocess
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('backup')

def main():
    # Déterminer le chemin du projet
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # S'assurer que nous sommes dans le répertoire du projet
    os.chdir(script_dir)
    
    logger.info("Démarrage de la sauvegarde automatique...")
    
    # Construire la commande Django
    python_executable = sys.executable
    manage_py = os.path.join(script_dir, 'manage.py')
    
    # Exécuter la commande de sauvegarde avec un maximum de 10 sauvegardes conservées
    try:
        result = subprocess.run(
            [python_executable, manage_py, 'backup_database', '--keep=10'],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de la sauvegarde: {e}")
        logger.error(f"Sortie d'erreur: {e.stderr}")
        return 1
    
    logger.info("Sauvegarde automatique terminée avec succès")
    return 0

if __name__ == '__main__':
    sys.exit(main()) 