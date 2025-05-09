#!/usr/bin/env python
import os
import django

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coupon.settings')
django.setup()

from belletin.models import Deliberation
from belletin.utils import encode_id

def update_deliberation_tokens():
    """Met à jour tous les tokens de délibération pour utiliser le format sécurisé."""
    # Obtenir toutes les délibérations
    deliberations = Deliberation.objects.all()
    
    # Nombre total de délibérations
    total = deliberations.count()
    print(f"Mise à jour des tokens pour {total} délibérations...")
    
    # Compteur pour les délibérations mises à jour
    updated = 0
    
    # Parcourir toutes les délibérations
    for deliberation in deliberations:
        old_token = deliberation.token
        
        # Générer un nouveau token au format sécurisé
        new_token = encode_id(deliberation.id, 'Deliberation')
        
        # Mettre à jour le token
        if old_token != new_token:
            deliberation.token = new_token
            deliberation.save(update_fields=['token'])
            updated += 1
            print(f"Délibération #{deliberation.id} mise à jour: {old_token} -> {new_token}")
    
    print(f"Terminé! {updated}/{total} tokens mis à jour.")

if __name__ == "__main__":
    update_deliberation_tokens() 