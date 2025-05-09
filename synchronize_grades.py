#!/usr/bin/env python
import os
import django
import sys

# Configuration de l'environnement Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coupon.settings')
django.setup()

from belletin.utils import synchronize_all_grades

if __name__ == "__main__":
    print("Démarrage de la synchronisation des notes...")
    result = synchronize_all_grades()
    
    print(f"\nSynchronisation terminée :")
    print(f"- Total de paires étudiant/cours traitées : {result['total']}")
    print(f"- Notes mises à jour avec succès : {result['updated']}")
    print(f"- Erreurs rencontrées : {result['errors']}")
    
    if result['errors'] > 0:
        print("\nDes erreurs se sont produites. Vérifiez les logs pour plus de détails.")
        sys.exit(1)
    else:
        print("\nToutes les notes ont été synchronisées avec succès !")
        sys.exit(0) 