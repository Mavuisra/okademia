#!/usr/bin/env python
import os
import sys
import logging
from datetime import datetime

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=f'app_init_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
)
logger = logging.getLogger(__name__)

logger.info("=== INITIALISATION DE L'APPLICATION ===")

# Configurer Django
try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coupon.settings')
    import django
    django.setup()
    logger.info("Django configuré avec succès")
except Exception as e:
    logger.error(f"Erreur lors de la configuration de Django: {str(e)}")
    sys.exit(1)

# Importer les modèles
try:
    from belletin.models import Deliberation, StudentDeliberation, Student, Grade, UE
    from belletin.utils import encode_id
    from django.utils import timezone
    from django.db.models import Avg, F
    logger.info("Modèles importés avec succès")
except Exception as e:
    logger.error(f"Erreur lors de l'importation des modèles: {str(e)}")
    sys.exit(1)

def init_app():
    """Initialise l'application avant le démarrage"""
    
    # 1. Vérifie et répare les tokens
    logger.info("Vérification des tokens...")
    try:
        # Délibérations sans token
        delibs_without_token = Deliberation.objects.filter(token__isnull=True)
        for delib in delibs_without_token:
            token = encode_id(delib.id, 'Deliberation')
            Deliberation.objects.filter(pk=delib.id).update(token=token)
            logger.info(f"Token généré pour délibération #{delib.id}")
        
        # Délibérations étudiants sans token
        student_delibs_without_token = StudentDeliberation.objects.filter(token__isnull=True)
        for student_delib in student_delibs_without_token:
            token = encode_id(student_delib.id, 'StudentDeliberation')
            StudentDeliberation.objects.filter(pk=student_delib.id).update(token=token)
            logger.info(f"Token généré pour délibération étudiant #{student_delib.id}")
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des tokens: {str(e)}")
    
    # 2. Calculer les moyennes et résultats des notes
    logger.info("Mise à jour des moyennes et résultats des notes...")
    try:
        grades_to_update = Grade.objects.all()
        update_count = 0
        
        for grade in grades_to_update:
            if grade.cc is not None and grade.mc is not None:
                moyenne = (grade.cc + grade.mc) / 2
                resultat = 'VALIDÉ' if moyenne >= 10 else 'NON VALIDÉ'
                
                Grade.objects.filter(pk=grade.id).update(
                    moyenne=moyenne,
                    resultat=resultat
                )
                update_count += 1
        
        logger.info(f"{update_count} notes mises à jour")
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des moyennes: {str(e)}")
    
    # 3. Vérifier et compléter les délibérations
    logger.info("Vérification des délibérations...")
    try:
        # S'assurer que les délibérations sont complétées
        Deliberation.objects.filter(status__in=['PENDING', 'IN_PROGRESS']).update(status='COMPLETED')
        
        # Valider les délibérations d'étudiants
        StudentDeliberation.objects.filter(validated=False).update(
            validated=True, 
            validated_at=timezone.now()
        )
        
        logger.info("Délibérations mises à jour")
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des délibérations: {str(e)}")
    
    logger.info("Initialisation terminée avec succès")
    return True

if __name__ == "__main__":
    try:
        success = init_app()
        if success:
            logger.info("Application initialisée avec succès!")
            print("Application initialisée avec succès!")
            sys.exit(0)
        else:
            logger.error("Échec de l'initialisation")
            print("Échec de l'initialisation. Consultez les logs pour plus de détails.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation: {str(e)}")
        print(f"Erreur lors de l'initialisation: {str(e)}")
        sys.exit(1) 