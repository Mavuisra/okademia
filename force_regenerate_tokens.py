#!/usr/bin/env python
import os
import django
import sys

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coupon.settings')
django.setup()

from belletin.models import Deliberation, StudentDeliberation
from belletin.utils import encode_id

def force_regenerate_all_tokens():
    """Force la régénération de tous les tokens dans la base de données."""
    print("Démarrage de la régénération forcée de tous les tokens...")
    
    # 1. Régénérer les tokens de délibération
    deliberations = Deliberation.objects.all()
    deliberations_count = deliberations.count()
    
    print(f"Régénération de {deliberations_count} tokens de délibération...")
    
    for delib in deliberations:
        old_token = delib.token
        
        # Générer un nouveau token avec l'ID actuel
        new_token = encode_id(delib.id, 'Deliberation')
        
        # Sauvegarder directement dans la base pour éviter les problèmes de cycle
        Deliberation.objects.filter(pk=delib.id).update(token=new_token)
        
        print(f"Délibération #{delib.id}: {old_token} → {new_token}")
    
    # 2. Régénérer les tokens de délibération étudiant
    student_delibs = StudentDeliberation.objects.all()
    student_delibs_count = student_delibs.count()
    
    print(f"\nRégénération de {student_delibs_count} tokens de délibération étudiant...")
    
    for student_delib in student_delibs:
        old_token = student_delib.token
        
        # Générer un nouveau token avec l'ID actuel
        new_token = encode_id(student_delib.id, 'StudentDeliberation')
        
        # Sauvegarder directement dans la base pour éviter les problèmes de cycle
        StudentDeliberation.objects.filter(pk=student_delib.id).update(token=new_token)
        
        print(f"Délibération étudiant #{student_delib.id}: {old_token} → {new_token}")
    
    # Vérifier les tokens après régénération
    invalid_delibs = Deliberation.objects.filter(token__isnull=True).count()
    invalid_student_delibs = StudentDeliberation.objects.filter(token__isnull=True).count()
    
    if invalid_delibs > 0 or invalid_student_delibs > 0:
        print(f"\nATTENTION: Il reste des tokens invalides après régénération: {invalid_delibs} délibérations, {invalid_student_delibs} délibérations étudiants")
        return False
    else:
        print("\nTous les tokens ont été correctement régénérés!")
        return True

if __name__ == "__main__":
    try:
        success = force_regenerate_all_tokens()
        if success:
            print("Régénération des tokens terminée avec succès!")
            sys.exit(0)
        else:
            print("La régénération des tokens a échoué!")
            sys.exit(1)
    except Exception as e:
        print(f"Erreur lors de la régénération des tokens: {str(e)}")
        sys.exit(1) 