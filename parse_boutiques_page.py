#!/usr/bin/env python3
"""
Parser spécifique pour extraire les boutiques de la page 'Nos boutiques'
Lit terresdecafe_knowledge_industrial_2025.json et met à jour la section boutiques
"""

import json
import re
from typing import List, Dict

def parse_boutiques_from_content(content: str) -> List[Dict]:
    """Parse le content de la page 'Nos boutiques' pour extraire les boutiques réelles"""
    boutiques = []
    
    # Trouver tous les blocs qui commencent par "BOUTIQUE XXX Adresse :"
    pattern = r'BOUTIQUE\s+([A-ZÉÈÊÀÂ\sÇŒÜÏ\-,]+?)\s+Adresse\s*:\s*(.+?)(?=BOUTIQUE\s+[A-Z]|$)'
    
    matches = re.finditer(pattern, content, re.DOTALL)
    
    for match in matches:
        nom = match.group(1).strip()
        bloc_contenu = match.group(2)
        
        # Limite le bloc à 1000 chars max
        bloc_contenu = bloc_contenu[:1000]
        
        # Extraire adresse (première ligne après "Adresse :")
        adresse_lines = bloc_contenu.split('\n')
        adresse_match = re.search(r'([0-9]+[^T\n]+?)(?:\s+Tel|$)', bloc_contenu)
        adresse = adresse_match.group(1).strip() if adresse_match else adresse_lines[0].strip()
        
        # Nettoyer l'adresse des artefacts
        adresse = re.sub(r'\s+Tel\s*:.*', '', adresse).strip()
        adresse = re.sub(r'\s+S\'y rendre.*', '', adresse).strip()
        
        # Extraire téléphone
        tel_match = re.search(r'Tel\s*:\s*([0-9\s]+)', bloc_contenu)
        telephone = tel_match.group(1).strip() if tel_match else ""
        
        # Extraire première ligne horaires
        horaires_match = re.search(r'((?:Lundi|Mardi|Mercredi|Jeudi|Vendredi|Samedi)[^\n]+)', bloc_contenu)
        horaires_ligne1 = horaires_match.group(1).strip() if horaires_match else ""
        
        # Nettoyer le nom
        nom_boutique = f"Terres de Café {nom.title()}"
        
        # Extraire ville et code postal de l'adresse
        ville_match = re.search(r',\s*([^,]+?)\s+(\d{5})', adresse)
        if ville_match:
            ville = ville_match.group(1).strip()
            code_postal = ville_match.group(2)
        else:
            # Format "Paris Xème"
            paris_match = re.search(r'Paris\s+(\d+)(?:ème|er)', adresse, re.IGNORECASE)
            if paris_match:
                arrondissement = paris_match.group(1)
                ville = f"Paris {arrondissement}e"
                code_postal = f"750{arrondissement.zfill(2)}"
            else:
                ville = "Paris"
                code_postal = ""
        
        # Extraire description courte
        desc_match = re.search(r'(?:fermeture|19h)\s+([A-Z][^\n]{20,200}?)\s+S\'y rendre', bloc_contenu, re.DOTALL)
        description_courte = desc_match.group(1).strip() if desc_match else ""
        
        # Construire description enrichie
        description_parts = [f"Boutique {nom_boutique}"]
        description_parts.append(f"\nAdresse: {adresse}")
        if telephone:
            description_parts.append(f"\nTéléphone: {telephone}")
        if horaires_ligne1:
            description_parts.append(f"\n\nHoraires: {horaires_ligne1}")
        if description_courte:
            description_parts.append(f"\n\n{description_courte}")
        
        description_parts.append(f"\n\nPour réserver ou commander: <a href=\"https://www.terresdecafe.com/fr/content/70-nos-boutiques\" target=\"_blank\">Voir la boutique</a>")
        
        boutique = {
            "name": nom_boutique,
            "telephone": telephone,
            "adresse": adresse,
            "ville": ville,
            "code_postal": code_postal,
            "statut": "ouvert",
            "url": "https://www.terresdecafe.com/fr/content/70-nos-boutiques",
            "horaires": horaires_ligne1,
            "description": "".join(description_parts)
        }
        
        boutiques.append(boutique)
        print(f"[OK] {nom_boutique} - {ville} - {telephone or 'Pas de tel'}")
    
    return boutiques


def main():
    # Lire le JSON industriel
    with open('terresdecafe_knowledge_industrial_2025.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Trouver la page "Nos boutiques"
    pages = data.get('pages_par_categorie', {}).get('autres', [])
    boutiques_page = None
    
    for page in pages:
        if page.get('url', '').endswith('70-nos-boutiques'):
            boutiques_page = page
            break
    
    if not boutiques_page:
        print("[ERROR] Page 'Nos boutiques' introuvable")
        return
    
    print(f"[INFO] Page trouvée: {boutiques_page['title']}")
    print(f"[INFO] Parsing des boutiques...\n")
    
    # Parser les boutiques
    boutiques = parse_boutiques_from_content(boutiques_page['content'])
    
    print(f"\n[OK] {len(boutiques)} boutiques extraites")
    
    # Remplacer la section boutiques
    data['boutiques'] = boutiques
    data['total_boutiques'] = len(boutiques)
    
    # Sauvegarder
    with open('terresdecafe_knowledge_industrial_2025.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] KB mise à jour: {len(boutiques)} boutiques")
    
    # Afficher résumé
    print("\n" + "="*60)
    print("BOUTIQUES EXTRAITES:")
    print("="*60)
    for b in boutiques:
        print(f"  • {b['name']}")
        print(f"    {b['adresse']}")
        print(f"    Tel: {b['telephone'] or 'N/A'}")
        print()


if __name__ == "__main__":
    main()
