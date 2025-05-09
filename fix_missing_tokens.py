#!/usr/bin/env python
import os
import django
import sys

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coupon.settings')
django.setup()

from belletin.models import Deliberation, StudentDeliberation
from belletin.utils import encode_id

def fix_missing_tokens():
    """Vérifie et répare tous les tokens manquants ou invalides dans la base de données."""
    print("Démarrage de la réparation des tokens...")
    
    # Vérifier et réparer les tokens de délibération
    deliberations_total = Deliberation.objects.count()
    deliberations_fixed = 0
    
    print(f"Vérification de {deliberations_total} délibérations...")
    
    for delib in Deliberation.objects.all():
        needs_update = False
        
        # Vérifier si le token est manquant
        if not delib.token:
            needs_update = True
            print(f"Délibération #{delib.id} - Token manquant")
        
        # Vérifier si le token contient l'ID correct
        elif f'"id":{delib.id}' not in delib.token and f'"id": {delib.id}' not in delib.token:
            needs_update = True
            print(f"Délibération #{delib.id} - Token ne contient pas l'ID correct")
        
        # Regénérer le token si nécessaire
        if needs_update:
            old_token = delib.token
            delib.token = encode_id(delib.id, 'Deliberation')
            
            # Sauvegarder directement dans la base pour éviter les problèmes de cycle
            Deliberation.objects.filter(pk=delib.id).update(token=delib.token)
            
            print(f"  → Token mis à jour: {old_token} → {delib.token}")
            deliberations_fixed += 1
    
    print(f"Délibérations réparées: {deliberations_fixed}/{deliberations_total}")
    
    # Vérifier et réparer les tokens de délibération étudiant
    student_delibs_total = StudentDeliberation.objects.count()
    student_delibs_fixed = 0
    
    print(f"\nVérification de {student_delibs_total} délibérations d'étudiants...")
    
    for student_delib in StudentDeliberation.objects.all():
        needs_update = False
        
        # Vérifier si le token est manquant
        if not student_delib.token:
            needs_update = True
            print(f"Délibération étudiant #{student_delib.id} - Token manquant")
        
        # Vérifier si le token contient l'ID correct
        elif f'"id":{student_delib.id}' not in student_delib.token and f'"id": {student_delib.id}' not in student_delib.token:
            needs_update = True
            print(f"Délibération étudiant #{student_delib.id} - Token ne contient pas l'ID correct")
        
        # Regénérer le token si nécessaire
        if needs_update:
            old_token = student_delib.token
            student_delib.token = encode_id(student_delib.id, 'StudentDeliberation')
            
            # Sauvegarder directement dans la base pour éviter les problèmes de cycle
            StudentDeliberation.objects.filter(pk=student_delib.id).update(token=student_delib.token)
            
            print(f"  → Token mis à jour: {old_token} → {student_delib.token}")
            student_delibs_fixed += 1
    
    print(f"Délibérations étudiants réparées: {student_delibs_fixed}/{student_delibs_total}")
    
    # Vérifier que les modifications ont été correctement appliquées
    print("\nVérification finale...")
    invalid_deliberations = Deliberation.objects.filter(token__isnull=True).count()
    invalid_student_delibs = StudentDeliberation.objects.filter(token__isnull=True).count()
    
    if invalid_deliberations > 0 or invalid_student_delibs > 0:
        print(f"ATTENTION: Il reste des tokens invalides: {invalid_deliberations} délibérations, {invalid_student_delibs} délibérations étudiants")
        print("Relancez ce script pour les réparer complètement.")
    else:
        print("Tous les tokens ont été correctement générés et mis à jour!")
    
    return deliberations_fixed + student_delibs_fixed

if __name__ == "__main__":
    try:
        fixed_count = fix_missing_tokens()
        print(f"\nTerminé avec succès! {fixed_count} tokens ont été réparés.")
        sys.exit(0)
    except Exception as e:
        print(f"Erreur lors de la réparation des tokens: {str(e)}")
        sys.exit(1) 