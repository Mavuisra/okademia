import os
import re

def fix_bulletin():
    # Chemins possibles pour le template
    paths = [
        "belletin/templates/student/bulletin.html",
        "templates/student/bulletin.html",
        "C:/Users/Mavu/Documents/coupon/belletin/templates/student/bulletin.html"
    ]
    
    template_path = None
    for path in paths:
        if os.path.exists(path):
            template_path = path
            break
    
    if not template_path:
        print("Template bulletin.html introuvable")
        return
    
    print(f"Correction du fichier: {template_path}")
    
    # Lecture du contenu
    with open(template_path, "r", encoding="utf-8") as file:
        content = file.read()
    
    # Remplacements
    content = content.replace(
        "grade.cc|add:grade.mc|floatformat:2|divisibleby:\"2\"|floatformat:2",
        "grade.cc|add:grade.mc|floatformat:2|dividedby:2|floatformat:2"
    )
    
    content = content.replace(
        "grade.cc|add:grade.mc|floatformat:2|divisibleby:\"2\"",
        "grade.cc|add:grade.mc|floatformat:2|dividedby:2"
    )
    
    # Écriture du fichier corrigé
    with open(template_path, "w", encoding="utf-8") as file:
        file.write(content)
    
    print("Correction terminée!")

if __name__ == "__main__":
    fix_bulletin() 