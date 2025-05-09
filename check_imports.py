#!/usr/bin/env python
"""
Script de test pour vérifier que les importations fonctionnent correctement
"""

try:
    # Test d'importation depuis belletin.utils
    print("Test d'importation depuis belletin.utils...")
    from belletin.utils import encode_id
    print("OK: encode_id importé depuis belletin.utils")
    
    # Test d'importation depuis belletin.templatetags.belletin_tags
    print("\nTest d'importation depuis belletin.templatetags.belletin_tags...")
    import belletin.templatetags.belletin_tags
    print("OK: belletin.templatetags.belletin_tags importé")
    
    # Test d'importation depuis belletin.models
    print("\nTest d'importation depuis belletin.models...")
    from belletin.models import Deliberation, StudentDeliberation
    print("OK: modèles importés depuis belletin.models")
    
    # Test d'importation de synchronize_all_grades
    print("\nTest d'importation de synchronize_all_grades...")
    from belletin.utils import synchronize_all_grades
    print("OK: synchronize_all_grades importé depuis belletin.utils")
    
    print("\nTous les tests d'importation ont réussi!")
    
except ImportError as e:
    print(f"Erreur d'importation: {e}")
except Exception as e:
    print(f"Autre erreur: {e}") 