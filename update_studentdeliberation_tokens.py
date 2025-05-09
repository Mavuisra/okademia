#!/usr/bin/env python
import os
import django

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coupon.settings')
django.setup()

from belletin.models import StudentDeliberation
from belletin.utils import encode_id

def update_studentdeliberation_tokens():
    """Met à jour tous les tokens de délibération d'étudiant pour utiliser le format sécurisé."""
    # Obtenir toutes les délibérations d'étudiants
    deliberations = StudentDeliberation.objects.all()
    
    # Nombre total de délibérations
    total = deliberations.count()
    print(f"Mise à jour des tokens pour {total} délibérations d'étudiants...")
    
    # Compteur pour les délibérations mises à jour
    updated = 0
    
    # Parcourir toutes les délibérations
    for deliberation in deliberations:
        old_token = deliberation.token
        
        # Générer un nouveau token au format sécurisé
        new_token = encode_id(deliberation.id, 'StudentDeliberation')
        
        # Mettre à jour le token
        if old_token != new_token:
            deliberation.token = new_token
            deliberation.save(update_fields=['token'])
            updated += 1
            print(f"Délibération étudiant #{deliberation.id} mise à jour: {old_token} -> {new_token}")
    
    print(f"Terminé! {updated}/{total} tokens mis à jour.")

if __name__ == "__main__":
    update_studentdeliberation_tokens() 