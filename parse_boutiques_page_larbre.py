#!/usr/bin/env python3
"""
Parser spécifique L'Arbre à Café - Extrait boutiques depuis page nos-boutiques
"""

import json
import re
from typing import List, Dict

def extract_boutiques_from_content(content: str) -> List[Dict]:
    """Parse le content de la page nos-boutiques"""
    boutiques = []
    
    # Patterns d'adresses L'Arbre à Café
    patterns = [
        r'(\d+\s+[Rr]ue[^,\n]+?\s+\d{5}\s+Paris)',  # 10 Rue du Nil 75002 Paris
        r'(\d+\s+[Bb]oulevard[^,\n]+?\s+\d{5}\s+Paris)',
        r'(\d+\s+[Aa]venue[^,\n]+?\s+\d{5}\s+Paris)',
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, content):
            adresse = match.group(1).strip()
            
            # Extraire code postal et arrondissement
            cp_match = re.search(r'(\d{5})', adresse)
            code_postal = cp_match.group(1) if cp_match else "75000"
            
            # Chercher téléphone près de l'adresse (dans les 200 chars)
            context_start = max(0, match.start() - 100)
            context_end = min(len(content), match.end() + 100)
            context = content[context_start:context_end]
            
            tel_match = re.search(r'0[1-9]([\s\.]?\d{2}){4}', context)
            telephone = tel_match.group(0) if tel_match else ""
            
            # Nettoyer format téléphone
            if telephone:
                telephone = re.sub(r'[\s\.]', ' ', telephone)
            
            # Extraire quartier de l'adresse
            quartier_match = re.search(r'Rue du (\w+)', adresse)
            if quartier_match:
                quartier = quartier_match.group(1)
                nom_boutique = f"L'Arbre à Café {quartier.title()}"
            else:
                nom_boutique = f"L'Arbre à Café Paris {code_postal[3:5]}"
            
            ville = "Paris"
            
            description_parts = [nom_boutique]
            if adresse:
                description_parts.append(f"\n\n📍 {adresse}")
            if telephone:
                description_parts.append(f"\n☎️ {telephone}")
            
            description_parts.append(f"\n\n<a href=\"https://larbreacafe.com/pages/nos-boutiques\" target=\"_blank\">Nos boutiques</a>")
            
            boutique = {
                "name": nom_boutique,
                "telephone": telephone,
                "adresse": adresse,
                "ville": ville,
                "code_postal": code_postal,
                "statut": "ouvert",
                "url": "https://larbreacafe.com/pages/nos-boutiques",
                "horaires": "",
                "description": "".join(description_parts)
            }
            
            # Éviter doublons
            if not any(b['adresse'] == adresse for b in boutiques):
                boutiques.append(boutique)
                print(f"[OK] {nom_boutique} - {telephone or 'Pas de tel'}")
    
    return boutiques


def main():
    # Lire le JSON
    with open('larbrecaf_knowledge_industrial_2025.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Trouver la page nos-boutiques
    pages = data.get('pages_par_categorie', {}).get('autres', [])
    boutiques_page = None
    
    for page in pages:
        if 'nos-boutiques' in page.get('url', '').lower():
            boutiques_page = page
            break
    
    if not boutiques_page:
        print("[ERROR] Page 'nos-boutiques' introuvable")
        return
    
    print(f"[INFO] Page trouvée: {boutiques_page['title']}")
    print(f"[INFO] Parsing des boutiques...\n")
    
    # Parser les boutiques
    boutiques = extract_boutiques_from_content(boutiques_page['content'])
    
    print(f"\n[OK] {len(boutiques)} boutiques extraites")
    
    # Remplacer la section boutiques
    data['boutiques'] = boutiques
    data['total_boutiques'] = len(boutiques)
    
    # Sauvegarder
    with open('larbrecaf_knowledge_industrial_2025.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] KB mise à jour: {len(boutiques)} boutiques")


if __name__ == "__main__":
    main()
